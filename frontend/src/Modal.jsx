import React from 'react';

const AuthorInfoModal = ({ authorInfo, onClose }) => {
  if (!authorInfo) return null;

  return (
    <div className="modal">
      <div className="modal-content">
        <span className="close" onClick={onClose}>&times;</span>
        <h2>{authorInfo.name}</h2>
        <img src={authorInfo.thumbnail} alt={authorInfo.name} className="author-thumbnail" />
        <p><strong>Affiliations:</strong> {authorInfo.affiliations}</p>
        <p><strong>Email:</strong> {authorInfo.email}</p>
        <p><strong>Website:</strong> <a href={authorInfo.website} target="_blank" rel="noreferrer">{authorInfo.website}</a></p>
        <p><strong>Citations (all):</strong> {authorInfo.citations.all}</p>
        <p><strong>h-index (all):</strong> {authorInfo.h_index.all}</p>
        <p><strong>i10-index (all):</strong> {authorInfo.i10_index.all}</p>
      </div>
    </div>
  );
};

export default AuthorInfoModal;
