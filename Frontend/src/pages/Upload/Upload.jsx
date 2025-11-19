import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileText, Upload as UploadIcon, X, Check, Loader2, FileJson } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Button from '../../System Design/Button';
import bookService from '../../services/bookService';

const Upload = () => {
  const [pdfFile, setPdfFile] = useState(null);
  const [jsonFile, setJsonFile] = useState(null);
  const [title, setTitle] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);
  const [error, setError] = useState('');
  const [createdBook, setCreatedBook] = useState(null);
  const [isQueued, setIsQueued] = useState(false);

  const onPdfDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles && acceptedFiles.length > 0) {
      setPdfFile(acceptedFiles[0]);
    }
  }, []);

  const onJsonDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles && acceptedFiles.length > 0) {
      setJsonFile(acceptedFiles[0]);
    }
  }, []);

  const { 
    getRootProps: getPdfRootProps, 
    getInputProps: getPdfInputProps, 
    isDragActive: isPdfDragActive 
  } = useDropzone({
    onDrop: onPdfDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const { 
    getRootProps: getJsonRootProps, 
    getInputProps: getJsonInputProps, 
    isDragActive: isJsonDragActive 
  } = useDropzone({
    onDrop: onJsonDrop,
    accept: {
      'application/json': ['.json']
    },
    multiple: false,
    maxSize: 5 * 1024 * 1024, // 5MB
  });

  const handleRemovePdfFile = (e) => {
    e.stopPropagation();
    setPdfFile(null);
    setUploadComplete(false);
  };

  const handleRemoveJsonFile = (e) => {
    e.stopPropagation();
    setJsonFile(null);
    setUploadComplete(false);
  };

  const navigate = useNavigate();

  const handleUpload = async () => {
    if (!pdfFile) {
      setError('Veuillez sélectionner un fichier PDF');
      return;
    }
    
    if (!title.trim()) {
      setError('Veuillez saisir un titre pour le document');
      return;
    }
    
    setIsUploading(true);
    setError('');
    
    try {
      // Créer un objet FormData pour l'upload multiple
      const formData = new FormData();
      formData.append('title', title.trim());
      formData.append('pdf_file', pdfFile);
      
      if (jsonFile) {
        formData.append('json_structure_file', jsonFile);
      }
      
      console.log('Envoi des données du livre:', {
        title: title.trim(),
        pdf_file: pdfFile.name,
        json_file: jsonFile ? jsonFile.name : 'Aucun fichier JSON'
      });
      
      const newBook = await bookService.createBook(formData);
      setCreatedBook(newBook);
      const queued = (newBook?.processing_status === 'queued' || newBook?.processing_status === 'processing');
      setIsQueued(queued);
      setUploadComplete(true);
      
      // Si le traitement est déjà terminé (cas rare), on peut rediriger. Sinon, on reste sur place.
      if (!queued) {
        setTimeout(() => {
          navigate(`/documents/${newBook.id}`);
        }, 1500);
      }
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
            
            <div className="mb-8">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Titre du document
              </label>
              <input
                type="text"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="Entrez un titre pour votre document"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={isUploading || uploadComplete}
              />
              
              {/* Catégories */}
              {/* <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Catégorie
                </label>
                <div className="flex gap-2 flex-wrap">
                  <button className="px-3 py-1.5 text-sm font-medium bg-primary-100 text-primary rounded-md hover:bg-primary-200">
                    Professionnel
                  </button>
                  <button className="px-3 py-1.5 text-sm font-medium bg-accent-100 text-accent rounded-md hover:bg-accent-200">
                    Éducation
                  </button>
                  <button className="px-3 py-1.5 text-sm font-medium bg-success-100 text-success rounded-md hover:bg-success-200">
                    Personnel
                  </button>
                  <button className="px-3 py-1.5 text-sm font-medium bg-warning-100 text-warning rounded-md hover:bg-warning-200">
                    Loisirs
                  </button>
                </div>
              </div> */}
            </div>
            
            <p className="text-sm text-gray-600 mb-4">
              Téléchargez vos fichiers pour créer un nouveau document
            </p>
            <p className="text-xs text-gray-500 mb-6">
              Le fichier PDF est obligatoire. Le fichier JSON est optionnel et permet de définir la structure du livre.
            </p>
          </div>
          
          {/* Zone d'upload PDF */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Fichier PDF avec balise <span className="text-red-500">*</span>
            </label>
            <div 
              {...getPdfRootProps()} 
              className={`p-6 text-center border-2 border-dashed rounded-lg transition-colors ${
                isPdfDragActive ? 'border-primary bg-primary-50' : 'border-gray-200 hover:border-primary'
              }`}
            >
              <input {...getPdfInputProps()} />
              
              {pdfFile ? (
                <div className="flex flex-col items-center">
                  <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center text-primary mb-3">
                    <FileText size={24} />
                  </div>
                  <p className="font-medium text-gray-900">{pdfFile.name}</p>
                  <p className="text-sm text-gray-500 mb-4">
                    {(pdfFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <button 
                    onClick={handleRemovePdfFile}
                    className="text-sm text-red-600 hover:text-red-800 flex items-center gap-1"
                  >
                    <X size={16} /> Supprimer
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center text-gray-400 mb-3">
                    <FileText size={24} />
                  </div>
                  <p className="text-sm text-gray-600">
                    {isPdfDragActive 
                      ? 'Déposez le PDF ici...' 
                      : 'Glissez votre PDF ici ou cliquez pour sélectionner'}
                  </p>
                  <p className="text-xs text-gray-400 mt-2">
                    Formats acceptés: .pdf (max 50MB)
                  </p>
                </div>
              )}
            </div>
          </div>
          
          {/* Zone d'upload JSON */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Fichier de structure JSON <span className="text-gray-400">(optionnel)</span>
            </label>
            <div 
              {...getJsonRootProps()} 
              className={`p-6 text-center border-2 border-dashed rounded-lg transition-colors ${
                isJsonDragActive ? 'border-accent bg-accent-50' : 'border-gray-200 hover:border-accent'
              }`}
            >
              <input {...getJsonInputProps()} />
              
              {jsonFile ? (
                <div className="flex flex-col items-center">
                  <div className="w-12 h-12 bg-accent-100 rounded-full flex items-center justify-center text-accent mb-3">
                    <FileJson size={24} />
                  </div>
                  <p className="font-medium text-gray-900">{jsonFile.name}</p>
                  <p className="text-sm text-gray-500 mb-4">
                    {(jsonFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <button 
                    onClick={handleRemoveJsonFile}
                    className="text-sm text-red-600 hover:text-red-800 flex items-center gap-1"
                  >
                    <X size={16} /> Supprimer
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center text-gray-400 mb-3">
                    <FileJson size={24} />
                  </div>
                  <p className="text-sm text-gray-600">
                    {isJsonDragActive 
                      ? 'Déposez le JSON ici...' 
                      : 'Glissez votre JSON ici ou cliquez pour sélectionner'}
                  </p>
                  <p className="text-xs text-gray-400 mt-2">
                    Formats acceptés: .json (max 5MB)
                  </p>
                </div>
              )}
            </div>
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
                  setPdfFile(null);
                  setJsonFile(null);
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
                disabled={!pdfFile || !title.trim() || isUploading || uploadComplete}
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
                    {isQueued ? 'Document créé, traitement en cours…' : 'Téléchargé avec succès !'}
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
          <div className={`mt-8 p-6 rounded-xl border ${isQueued ? 'bg-blue-50 border-blue-200' : 'bg-success-50 border-success-200'}`}>
            <div className="flex items-start gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isQueued ? 'bg-blue-100 text-blue-700' : 'bg-success-100 text-success'}`}>
                <Check size={16} />
              </div>
              <div>
                <h3 className={`font-medium ${isQueued ? 'text-blue-900' : 'text-success-800'}`}>
                  {isQueued ? 'Document créé — traitement en cours' : 'Document téléchargé avec succès !'}
                </h3>
                <p className={`text-sm mt-1 ${isQueued ? 'text-blue-800' : 'text-success-700'}`}>
                  {isQueued
                    ? "Le fichier a été importé. L’extraction et la génération des QCM continuent en arrière-plan. Vous pourrez ouvrir le document une fois le traitement terminé."
                    : "Votre document a été analysé avec succès. Vous pouvez maintenant le consulter dans votre bibliothèque."}
                </p>
                <div className="mt-4 flex gap-3">
                  <Button
                    variant={isQueued ? 'secondary' : 'primary'}
                    size="sm"
                    onClick={() => navigate('/')}
                  >
                    Retour à l'accueil
                  </Button>
                  {createdBook?.id && !isQueued && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => navigate(`/documents/${createdBook.id}`)}
                    >
                      Voir le document
                    </Button>
                  )}
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
