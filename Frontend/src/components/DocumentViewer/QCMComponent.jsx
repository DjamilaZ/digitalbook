import React, { useState } from 'react';
import { CheckCircle, XCircle, RotateCcw } from 'lucide-react';

const QCMComponent = ({ qcm }) => {
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [showResults, setShowResults] = useState(false);

  const handleAnswerSelect = (questionId, responseId) => {
    setSelectedAnswers(prev => ({
      ...prev,
      [questionId]: responseId
    }));
  };

  const calculateScore = () => {
    let correctAnswers = 0;
    let totalQuestions = qcm.questions.length;

    qcm.questions.forEach(question => {
      const selectedResponse = selectedAnswers[question.id];
      if (selectedResponse) {
        const response = question.responses.find(r => r.id === selectedResponse);
        if (response && response.is_correct) {
          correctAnswers++;
        }
      }
    });

    return { correctAnswers, totalQuestions, percentage: Math.round((correctAnswers / totalQuestions) * 100) };
  };

  const resetQuiz = () => {
    setSelectedAnswers({});
    setShowResults(false);
  };

  const score = calculateScore();

  return (
    <div className="w-full bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200 p-6 my-6">
      {/* Header du QCM */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-bold text-blue-900 flex items-center gap-2">
            📝 {qcm.title}
          </h3>
          {qcm.description && (
            <p className="text-blue-700 text-sm mt-1">{qcm.description}</p>
          )}
          <p className="text-blue-600 text-xs mt-1">
            {qcm.question_count} question{qcm.question_count > 1 ? 's' : ''}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {showResults && (
            <div className="bg-white px-3 py-1 rounded-full border border-blue-300">
              <span className="text-blue-800 font-semibold">
                {score.correctAnswers}/{score.totalQuestions} ({score.percentage}%)
              </span>
            </div>
          )}
          
          <button
            onClick={resetQuiz}
            className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded-md text-sm flex items-center gap-1 transition-colors"
          >
            <RotateCcw size={14} />
            Réinitialiser
          </button>
          
          <button
            onClick={() => setShowResults(!showResults)}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
              showResults 
                ? 'bg-gray-500 hover:bg-gray-600 text-white' 
                : 'bg-green-500 hover:bg-green-600 text-white'
            }`}
          >
            {showResults ? 'Cacher résultats' : 'Voir résultats'}
          </button>
        </div>
      </div>

      {/* Questions */}
      <div className="space-y-6">
        {qcm.questions.map((question, questionIndex) => (
          <div key={question.id} className="bg-white rounded-lg border border-blue-100 p-4">
            <div className="flex items-start gap-3">
              <div className="bg-blue-100 text-blue-800 w-6 h-6 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 mt-0.5">
                {questionIndex + 1}
              </div>
              
              <div className="flex-1">
                <h4 className="font-semibold text-gray-800 mb-3">{question.text}</h4>
                
                {/* Réponses */}
                <div className="space-y-2">
                  {question.responses.map((response, responseIndex) => {
                    const isSelected = selectedAnswers[question.id] === response.id;
                    const showCorrectness = showResults && isSelected;
                    
                    return (
                      <div
                        key={response.id}
                        onClick={() => !showResults && handleAnswerSelect(question.id, response.id)}
                        className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                          isSelected
                            ? showCorrectness
                              ? response.is_correct
                                ? 'border-green-500 bg-green-50'
                                : 'border-red-500 bg-red-50'
                              : 'border-blue-500 bg-blue-50'
                            : showResults && response.is_correct
                            ? 'border-green-300 bg-green-50'
                            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                              isSelected
                                ? showCorrectness
                                  ? response.is_correct
                                    ? 'border-green-500 bg-green-500'
                                    : 'border-red-500 bg-red-500'
                                  : 'border-blue-500 bg-blue-500'
                                : showResults && response.is_correct
                                ? 'border-green-500 bg-green-500'
                                : 'border-gray-300'
                            }`}>
                              {isSelected && (
                                <div className={`w-2 h-2 rounded-full bg-white`}></div>
                              )}
                              {showResults && response.is_correct && !isSelected && (
                                <CheckCircle size={12} className="text-white" />
                              )}
                            </div>
                            <span className={`${
                              showCorrectness
                                ? response.is_correct
                                  ? 'text-green-800 font-medium'
                                  : 'text-red-800'
                                : showResults && response.is_correct
                                ? 'text-green-800 font-medium'
                                : 'text-gray-700'
                            }`}>
                              {response.text}
                            </span>
                          </div>
                          
                          {showCorrectness && (
                            <div className="flex-shrink-0">
                              {response.is_correct ? (
                                <CheckCircle size={18} className="text-green-500" />
                              ) : (
                                <XCircle size={18} className="text-red-500" />
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
                
                {/* Feedback après soumission */}
                {showResults && selectedAnswers[question.id] && (
                  <div className={`mt-3 p-2 rounded-md text-sm ${
                    question.responses.find(r => r.id === selectedAnswers[question.id])?.is_correct
                      ? 'bg-green-100 text-green-800 border border-green-200'
                      : 'bg-red-100 text-red-800 border border-red-200'
                  }`}>
                    {question.responses.find(r => r.id === selectedAnswers[question.id])?.is_correct
                      ? '✅ Bonne réponse !'
                      : '❌ Mauvaise réponse'
                    }
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Score final */}
      {showResults && (
        <div className={`mt-6 p-4 rounded-lg border-2 text-center ${
          score.percentage >= 70
            ? 'border-green-300 bg-green-50'
            : score.percentage >= 50
            ? 'border-yellow-300 bg-yellow-50'
            : 'border-red-300 bg-red-50'
        }`}>
          <div className="text-2xl font-bold mb-2">
            {score.percentage >= 70 ? '🎉' : score.percentage >= 50 ? '👍' : '📚'}
          </div>
          <h4 className="text-lg font-semibold mb-1">
            Score final : {score.correctAnswers}/{score.totalQuestions} ({score.percentage}%)
          </h4>
          <p className="text-sm">
            {score.percentage >= 70
              ? 'Excellent ! Vous avez bien maîtrisé ce chapitre.'
              : score.percentage >= 50
              ? 'Bon travail ! Continuez à réviser pour améliorer votre score.'
              : 'Continuez à étudier ce chapitre et réessayez plus tard.'
            }
          </p>
        </div>
      )}
    </div>
  );
};

export default QCMComponent;
