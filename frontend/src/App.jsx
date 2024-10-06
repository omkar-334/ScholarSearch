import React, { useState, useEffect } from 'react';
import PublicationList from './components/PublicationList';
import axios from 'axios';

const App = () => {
  const [publications, setPublications] = useState([]);
  const [filters, setFilters] = useState({ author: '', year: '' });




  return (
    <div>
      <PublicationList  />
    </div>
  );
};

export default App;
