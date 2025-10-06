import React from 'react';
import { Home, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function NotFound() {
  const navigate = useNavigate();

  const handleGoHome = () => {
    navigate('/');
  };

  const handleGoBack = () => {
    window.history.back();
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
      <div className="rounded-full bg-primary/10 p-6 mb-6">
        <Home className="w-12 h-12 text-primary" />
      </div>

      <h1 className="text-2xl font-bold text-text mb-3">
        Page Not Found
      </h1>

      <p className="text-muted mb-8 max-w-md leading-relaxed">
        Sorry, the page you're looking for doesn't exist or has been moved.
        Let's get you back on track with your health journey.
      </p>

      <div className="flex gap-4 flex-col sm:flex-row">
        <button
          onClick={handleGoBack}
          className="flex items-center gap-2 px-6 py-3 bg-muted/20 text-text rounded-xl hover:bg-muted/30 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Go Back
        </button>

        <button
          onClick={handleGoHome}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-navy rounded-xl hover:bg-primary/90 transition-colors font-medium"
        >
          <Home className="w-4 h-4" />
          Go Home
        </button>
      </div>
    </div>
  );
}

export default NotFound;
