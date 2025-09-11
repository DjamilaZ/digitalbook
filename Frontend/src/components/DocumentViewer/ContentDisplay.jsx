import React from 'react';
import './ContentDisplay.css';

const ContentDisplay = ({ selectedItem }) => {
  if (!selectedItem) {
    return (
      <div className="content-display">
        <div className="empty-state">
          <div className="empty-icon">📄</div>
          <h3>Sélectionnez un élément dans le sommaire</h3>
          <p>Cliquez sur un chapitre, une section ou une sous-section pour afficher son contenu ici.</p>
        </div>
      </div>
    );
  }

  const { type, data } = selectedItem;
  
  // Vérifier si les données existent
  if (!data) {
    return (
      <div className="content-display">
        <div className="empty-state">
          <div className="empty-icon">⚠️</div>
          <h3>Données non disponibles</h3>
          <p>Les données pour cet élément ne sont pas disponibles.</p>
        </div>
      </div>
    );
  }

  const renderContent = () => {
    if (!data.content || typeof data.content !== 'string' || data.content.trim() === '') {
      return (
        <div className="no-content">
          <p>Cet élément ne contient pas de texte.</p>
        </div>
      );
    }

    // Formater le contenu pour un meilleur affichage
    const formatContent = (content) => {
      return content.split('. ').map((sentence, index) => {
        if (sentence.trim() === '') return null;
        return (
          <p key={index} className="content-paragraph">
            {sentence.trim() + (index < content.split('. ').length - 1 ? '.' : '')}
          </p>
        );
      }).filter(Boolean);
    };

    return formatContent(data.content);
  };

  const getBreadcrumb = () => {
    const breadcrumb = [];
    
    if (selectedItem.type === 'chapter') {
      if (data && data.order !== undefined && data.title) {
        breadcrumb.push(`Chapitre ${data.order + 1}: ${data.title}`);
      }
    } else if (selectedItem.type === 'section') {
      const chapter = selectedItem.chapterData;
      if (chapter && chapter.order !== undefined && chapter.title) {
        breadcrumb.push(`Chapitre ${chapter.order + 1}: ${chapter.title}`);
      }
      if (data && data.order !== undefined && data.title) {
        breadcrumb.push(`Section ${data.order + 1}: ${data.title}`);
      }
    } else if (selectedItem.type === 'subsection') {
      const chapter = selectedItem.chapterData;
      const section = selectedItem.sectionData;
      if (chapter && chapter.order !== undefined && chapter.title) {
        breadcrumb.push(`Chapitre ${chapter.order + 1}: ${chapter.title}`);
      }
      if (section && section.order !== undefined && section.title) {
        breadcrumb.push(`Section ${section.order + 1}: ${section.title}`);
      }
      if (data && data.order !== undefined && data.title) {
        breadcrumb.push(`Sous-section ${data.order + 1}: ${data.title}`);
      }
    }
    
    return breadcrumb;
  };

  const getTypeIcon = () => {
    switch (type) {
      case 'chapter':
        return '📚';
      case 'section':
        return '📑';
      case 'subsection':
        return '📄';
      default:
        return '📄';
    }
  };

  return (
    <div className="content-display">
      <div className="content-header">
        <div className="breadcrumb">
          {getBreadcrumb().map((item, index) => (
            <React.Fragment key={index}>
              <span className="breadcrumb-item">{item}</span>
              {index < getBreadcrumb().length - 1 && (
                <span className="breadcrumb-separator">›</span>
              )}
            </React.Fragment>
          ))}
        </div>
        
        <div className="content-title">
          <span className="type-icon">{getTypeIcon()}</span>
          <h1>{data.title || 'Titre non disponible'}</h1>
          <span className="content-number">(ID: {data.id || 'N/A'})</span>
        </div>
      </div>

      <div className="content-body">
        <div className="content-text">
          {renderContent()}
        </div>

        {/* Afficher les images si elles existent */}
        {Array.isArray(data.images) && data.images.length > 0 && (
          <div className="content-images">
            <h3>Images</h3>
            <div className="images-grid">
              {data.images.map((image, index) => (
                <div key={index} className="image-item">
                  <img 
                    src={image.url || ''} 
                    alt={image.caption || `Illustration ${index + 1}`} 
                    className="content-image"
                  />
                  <p className="image-caption">{image.caption || `Image ${index + 1}`}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Afficher les tableaux s'ils existent */}
        {data.tables && data.tables.length > 0 && (
          <div className="content-tables">
            <h3>Tableaux</h3>
            {data.tables.map((table, index) => (
              <div key={index} className="table-item">
                <div className="table-content">
                  {table.content.split('\n').map((line, lineIndex) => (
                    <div key={lineIndex} className="table-line">{line}</div>
                  ))}
                </div>
                <p className="table-caption">{table.caption || `Tableau ${index + 1}`}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ContentDisplay;
