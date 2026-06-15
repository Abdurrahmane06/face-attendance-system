import React, { useEffect } from 'react';
import FaceCamera from '../components/FaceCamera';

const FaceRecognition = () => {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Reconnaissance faciale</h1>
      <p className="text-gray-500">
        Utilisez la webcam pour pointer votre présence par reconnaissance faciale.
      </p>
      <FaceCamera />
    </div>
  );
};

export default FaceRecognition;
