import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileText, Upload as UploadIcon, X, Check, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Button from '../../System Design/Button';
import bookService from '../../services/bookService';

const Upload = () => {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);
  const [error, setError] = useState('');

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles && acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const handleRemoveFile = (e) => {
    e.stopPropagation();
    setFile(null);
    setUploadComplete(false);
  };

  const navigate = useNavigate();

  const handleUpload = async () => {
    if (!file) {
      setError('Veuillez sélectionner un fichier');
      return;
    }
    
    if (!title.trim()) {
      setError('Veuillez saisir un titre pour le document');
      return;
    }
    
    setIsUploading(true);
    setError('');
    
    try {
      // Créer un objet avec les données du formulaire
      const bookData = {
        title: title.trim(),
        pdf_file: file
      };
      
      console.log('Envoi des données du livre:', {
        title: bookData.title,
        file: bookData.pdf_file ? bookData.pdf_file.name : 'Aucun fichier'
      });
      
      const newBook = await bookService.createBook(bookData);
      setUploadComplete(true);
      
      // Rediriger vers la page du livre après un court délai
      setTimeout(() => {
        navigate(`/documents/${newBook.id}`);
      }, 1500);
    } catch (error) {
      console.error('Erreur lors du téléchargement:', error);
      const errorMessage = error.response?.data?.message || 
                         error.response?.data?.detail || 
                         'Une erreur est survenue lors du téléchargement. Veuillez réessayer.';
      setError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold mb-8">Télécharger un document</h1>
        
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold mb-4">Importer un document</h2>
            
            <div className="mb-4">
              <label htmlFor="document-title" className="block text-sm font-medium text-gray-700 mb-1">
                Titre du document <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="document-title"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Entrez le titre du document"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={isUploading || uploadComplete}
              />
            </div>
            
            <p className="text-sm text-gray-600 mb-2">
              Glissez et déposez votre fichier PDF ici ou cliquez pour le sélectionner
            </p>
            <p className="text-xs text-gray-500">
              Taille maximale : 50MB. Formats acceptés : .pdf
            </p>
          </div>
          
          <div 
            {...getRootProps()} 
            className={`p-8 text-center border-2 border-dashed rounded-lg mx-6 my-4 transition-colors ${
              isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300'
            }`}
          >
            <input {...getInputProps()} />
            
            {file ? (
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 mb-3">
                  <FileText size={24} />
                </div>
                <p className="font-medium text-gray-900">{file.name}</p>
                <p className="text-sm text-gray-500 mb-4">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <button 
                  onClick={handleRemoveFile}
                  className="text-sm text-red-600 hover:text-red-800 flex items-center gap-1"
                >
                  <X size={16} /> Supprimer
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center text-gray-400 mb-3">
                  <UploadIcon size={24} />
                </div>
                <p className="text-sm text-gray-600">
                  {isDragActive 
                    ? 'Déposez le fichier ici...' 
                    : 'Formats acceptés: .pdf (max 50MB)'}
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  ou cliquez pour parcourir vos fichiers
                </p>
              </div>
            )}
          </div>
          
          <div className="p-6">
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
                {error}
              </div>
            )}
            
            <div className="flex flex-col sm:flex-row justify-end gap-3">
              <Button
                onClick={() => {
                  setFile(null);
                  setTitle('');
                  setError('');
                }}
                variant="secondary"
                size="md"
                disabled={isUploading || uploadComplete}
                className="w-full sm:w-auto"
              >
                Annuler
              </Button>
              
              <Button
                onClick={handleUpload}
                disabled={!file || !title.trim() || isUploading || uploadComplete}
                variant="primary"
                size="md"
                className="w-full sm:w-auto"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="animate-spin mr-2 h-4 w-4" />
                    Téléchargement...
                  </>
                ) : uploadComplete ? (
                  <>
                    <Check className="mr-2 h-4 w-4" />
                    Téléchargé avec succès !
                  </>
                ) : (
                  <>
                    <UploadIcon className="mr-2 h-4 w-4" />
                    Télécharger le document
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
        
        {uploadComplete && (
          <div className="mt-8 p-6 bg-green-50 border border-green-200 rounded-xl">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center text-green-600 flex-shrink-0">
                <Check size={16} />
              </div>
              <div>
                <h3 className="font-medium text-green-800">Document téléchargé avec succès !</h3>
                <p className="text-sm text-green-700 mt-1">
                  Votre document a été analysé avec succès. Vous pouvez maintenant le consulter dans votre bibliothèque.
                </p>
                <div className="mt-4 flex gap-3">
                  <Button variant="primary" size="sm">
                    Voir le document
                  </Button>
                  <Button variant="secondary" size="sm">
                    Retour à l'accueil
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Upload;
