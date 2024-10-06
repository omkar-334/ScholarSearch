import React, { useState, useRef, useEffect } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import axios from 'axios';
import * as XLSX from 'xlsx';
import * as docx from 'docx';
import Select from 'react-select';


const ITEMS_PER_PAGE = 10;

const PublicationList = () => {
  const [publications, setPublications] = useState({});
  const [startYear, setStartYear] = useState(null);
  const [endYear, setEndYear] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [excelFile, setExcelFile] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [sortOrder, setSortOrder] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [authorNames, setAuthorNames] = useState([]);
  const [currentAuthorIndex, setCurrentAuthorIndex] = useState(0);
  const [showingAuthor, setShowingAuthor] = useState(''); 
  const [selectedAuthors, setSelectedAuthors] = useState([]);
  const fileInputRef = useRef(null);
  const [fadeClass, setFadeClass] = useState('fade-in');
  

  useEffect(() => {
    if (searchQuery) {
      const authors = searchQuery.split(',').map(author => author.trim());
      setAuthorNames(authors);
    }
  }, [searchQuery]);

  useEffect(() => {
    if (authorNames.length > 0) {
      const interval = setInterval(() => {
        setFadeClass('fade-out');
        setTimeout(() => {
          setShowingAuthor(authorNames[currentAuthorIndex]);
          setFadeClass('fade-in');
          setCurrentAuthorIndex(prevIndex => (prevIndex + 1) % authorNames.length);
        }, 1000);
      }, 3000);

      return () => clearInterval(interval);
    }
  }, [authorNames, currentAuthorIndex]);

  const fetchPublications = async (authors) => {
    setLoading(true);
    setPublications({});
    setHasSearched(true);
    try {
      const authorList = authors.split(',').map(author => author.trim());
      const url = `https://gis-python-413005.el.r.appspot.com/query?${authorList.map(author => `author=${encodeURIComponent(author)}`).join('&')}&api_key=${import.meta.env.SCHOLARSEARCH_API_KEY}`;
      console.log('Fetching from URL:', url);
      
      const response = await axios.get(url);
      console.log('Raw response:', response);
      
      if (response.data) {
        const publicationsData = {};
        
        Object.keys(response.data).forEach(author => {
          publicationsData[author] = response.data[author].data; 
          console.log(response.data[author].info)

        });
  
        console.log('Processed data:', publicationsData);
        setPublications(publicationsData);
        setSelectedAuthors(Object.keys(publicationsData));
      } else {
        console.error('Unexpected response structure:', response.data);
        setPublications({});
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      if (error.response) {
        console.error('Error response:', error.response.data);
      }
      setPublications({});
    } finally {
      setLoading(false);
    }
  };
  

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setExcelFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const json = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
        const authors = json.map(row => row[0]).filter(author => author).join(',');
        setSearchQuery(authors);
        fetchPublications(authors);
      };
      reader.readAsArrayBuffer(file);
    }
  };

  const handleAuthorSelection = (author) => {
    setSelectedAuthors(prev => 
      prev.includes(author) 
        ? prev.filter(a => a !== author) 
        : [...prev, author]
    );
  };

  const searchFilter = (pub) => {
    const term = searchTerm.toLowerCase();
    
    // Add null checks for each property before accessing them
    return (
      (pub?.title && pub.title.toLowerCase().includes(term)) ||
      (pub?.authors && pub.authors.join(', ').toLowerCase().includes(term)) ||
      (pub?.abstract && pub.abstract.toLowerCase().includes(term)) ||
      (pub?.link && pub.link.toLowerCase().includes(term)) ||
      (pub?.year && pub.year.toString().includes(term)) ||
      (pub?.source && pub.source.toLowerCase().includes(term))
    );
  };
  
  

  const filteredPublications = Object.entries(publications)
    .filter(([author, pubs]) => selectedAuthors.includes(author))
    .flatMap(([author, pubs]) => pubs)
    .filter(searchFilter)
    .filter(pub => {
      const pubYear = pub.year;
      return (!startYear || pubYear >= startYear) && (!endYear || pubYear <= endYear);
    });

  const sortedPublications = [...filteredPublications].sort((a, b) => {
    const yearA = a.year;
    const yearB = b.year;
    return sortOrder === 'ascending' ? yearA - yearB : yearB - yearA;
  });

  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedPublications = sortedPublications.slice(startIndex, endIndex);

  const exportToExcel = () => {
    const ws = XLSX.utils.json_to_sheet(filteredPublications.map(pub => ({
      Title: pub.title,
      Date: pub.year,
      URL: pub.link,
      Abstract: pub.abstract,
      Authors: pub.authors.join(', '),
      Source: pub.source || 'N/A'
    })));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Publications');
    XLSX.writeFile(wb, 'FilteredPublications.xlsx');
  };

  const exportToBibTeX = () => {
    const bibtexEntries = filteredPublications.map((pub, index) => {
      const authors = pub.authors.join(' and ');
      return `@article{publication${index + 1},
    author    = {${authors}},
    title     = {${pub.title}},
    journal   = {${pub.source || 'Journal Name'}},
    year      = {${pub.year}},
    url       = {${pub.link}},
    abstract  = {${pub.abstract}}
  }`;
    }).join('\n\n');
  
    const blob = new Blob([bibtexEntries], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'FilteredPublications.bib';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };


  const exportToWord = () => {
    const doc = new docx.Document({
      sections: [
        {
          properties: {},
          children: [
            new docx.Paragraph({
              children: [
                new docx.TextRun("Publications List"),
              ],
              heading: docx.HeadingLevel.HEADING_1,
            }),
            ...filteredPublications.map(pub => 
              new docx.Paragraph({
                children: [
                  new docx.TextRun(`Title: ${pub.title}`),
                  new docx.TextRun(`Date: ${pub.year}`),
                  new docx.TextRun(`URL: ${pub.link}`),
                  new docx.TextRun(`Abstract: ${pub.abstract}`),
                  new docx.TextRun(`Authors: ${pub.authors.join(', ')}`),
                  new docx.TextRun(`Source: ${pub.source || 'N/A'}`),
                  new docx.TextRun("\n"), // Add a new line for separation
                ],
              })
            ),
          ],
        },
      ],
    });

    docx.Packer.toBlob(doc).then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'FilteredPublications.docx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    });
  };

  const totalPages = Math.ceil(filteredPublications.length / ITEMS_PER_PAGE);

  return (
    <div className="main">
      <div className="header">
        <h1>ScholarSearch</h1>
      </div>
      <div className="publication-list">
        <div className="filter-section">
          <button
            className="hamburger-menu"
            onClick={() => setShowFilters(!showFilters)}
            style={{ display: 'none' }}
          >
            <i className="ri-menu-line"></i>
          </button>

          <div className={`filter-content ${showFilters ? 'show' : ''}`}>
            <div className="filter-item-search">
              <p>Extract Publications by Authors</p>
              <div className="search-bar">
                <input
                  id="search-query"
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                 
                />
                <button
                  className="search-button"
                  onClick={() => fetchPublications(searchQuery)}
                  disabled={searchQuery.length < 3}
                >
                  {loading ? <i className="loader ri-loader-4-line"></i> : <i className="ri-search-line"></i>}
                </button>
              </div>
            </div>

            <input
              type="file"
              id="file-upload"
              accept=".xlsx"
              onChange={handleFileUpload}
              ref={fileInputRef}
              style={{ display: 'none' }}
            />
            <button
              className="custom-file-upload"
              onClick={() => fileInputRef.current.click()}
            >
              Import Excel File <i className="ri-file-excel-2-fill"></i>
            </button>
            <hr />
            <div className="filter-item author-filter">
              <p className='pubyearfilter'>Filter by Authors:</p>
              {Object.keys(publications).map(author => (
                <label key={author} className="author-checkbox custom-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedAuthors.includes(author)}
                    onChange={() => handleAuthorSelection(author)}
                  />
                  <span className="checkmark"></span>
                  {author}
                </label>
              ))}
            </div>
                   
            <hr />

            <p className='pubyearfilter'>Filter by Publication Year</p>
            <div className="filter-item">
              
              <DatePicker
                id="start-year"
                selected={startYear ? new Date(startYear, 0, 1) : null}
                onChange={(date) => setStartYear(date ? date.getFullYear() : null)}
                showYearPicker
                dateFormat="yyyy"
                placeholderText="From "
              />

              <DatePicker
                id="end-year"
                selected={endYear ? new Date(endYear, 0, 1) : null}
                onChange={(date) => setEndYear(date ? date.getFullYear() : null)}
                showYearPicker
                dateFormat="yyyy"
                placeholderText="To"
              />    
            </div>

            <div className="whiteline"></div>

           

            <button className="clear-button" onClick={() => { setStartYear(null); setEndYear(null); setSelectedAuthors(Object.keys(publications)); }}>
              Clear Filters <i className="ri-delete-back-2-line"></i>
            </button>
            <button className="export-button" onClick={exportToExcel}>
              Export as Excel <i className="ri-file-excel-2-fill"></i>
            </button>
            <button className="export-button bibtex-button" onClick={exportToBibTeX}>
              Export as BibTeX <i className="ri-sticky-note-line"></i>
            </button>
            <button className="export-button word-button" onClick={exportToWord}>
          Export as Word <i className="ri-file-word-2-fill"></i>
        </button>
          </div>
        </div>

        <div className="publication-list-items">
          {!hasSearched && (
            <div className="how-to-use">
              <h2>How to Use ScholarSearch</h2>
              <ol>
                <li>Enter authors' names in the search bar (e.g., "Yann LeCun, Andrew Ng") and click the search button.</li>
                <li>Alternatively, upload an Excel file containing a list of authors.</li>
                <li>Use the author checkboxes to filter publications by specific authors.</li>
                <li>Use the date pickers to filter publications by year range.</li>
                <li>Use the search bar to filter results by author, title, abstract, URL, year, or source.</li>
                <li>Sort the results by date using the dropdown menu.</li>
                <li>Navigate through the results using the pagination controls at the bottom.</li>
                <li>Export your filtered results as an Excel file or BibTeX format for further use.</li>
              </ol>
            </div>
          )}

          {loading ? (
            <div className="loading-indicator">
              <i className="loader loader-large ri-loader-4-line"></i>
              <p>Searching for the publications of the author <span className={`author-name ${fadeClass}`}>{showingAuthor}</span></p>
            </div>
          ) : Object.keys(publications).length > 0 ? (
            <>
              <div className="filter-by-date and searchbar">
                <div className="search-bar sb2">
                  <i className="ri-search-line"></i>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search by author, title, abstract, URL, year, or source"
                  />
                </div>
                <div className='df'>
                  <p className='sortp'>Sort by: </p>
                  <select
                    value={sortOrder || ''}
                    onChange={(e) => setSortOrder(e.target.value)}
                  >
                    <option value="">Select Order</option>
                    <option value="ascending">Oldest</option>
                    <option value="descending">Newest</option>
                  </select>
                </div>
              </div>
              
              {paginatedPublications.length > 0 ? (
                <ul>
                  {paginatedPublications.map((pub, index) => (
                    <li key={index} className="publication-item">
                      <h3 className="publication-title">{pub.title}</h3>
                      <p><strong>Date:</strong> {pub.year}</p>
                      <p><strong>URL:</strong> <a href={pub.link} target="_blank" rel="noopener noreferrer">{pub.link}</a></p>
                      <p><strong>Abstract:</strong> {pub.abstract}</p>
                      <p><strong>Authors:</strong> {pub.authors.join(', ')}</p>
                      <p><strong>Source:</strong> {pub.source || 'N/A'}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No publications found matching your search criteria.</p>
              )}
              <div className="pagination-controls">
              <button
                onClick={() => handlePageChange(1)}
                disabled={currentPage === 1}
              >
                <i className="ri-arrow-left-double-line"></i>
              </button>
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                <i className="ri-arrow-left-s-line"></i>
              </button>
              <span>Page {currentPage} of {totalPages}</span>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                <i className="ri-arrow-right-s-line"></i>
              </button>
              <button
                onClick={() => handlePageChange(totalPages)}
                disabled={currentPage === totalPages}
              >
                <i className="ri-arrow-right-double-line"></i>
              </button>
            </div>
          </>
        ) : hasSearched ? (
          <p>No publications found matching your search criteria.</p>
        ) : (
          <p></p>
        )}
      </div>
    </div>
  </div>
);
};

export default PublicationList;