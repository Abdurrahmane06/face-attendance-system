import React, { useEffect, useRef, useState } from 'react';
import { useFaceCamera } from '../hooks/useFaceCamera';
import { attendanceService } from '../services/attendanceService';
import { useAuth } from '../hooks/useAuth';
import Button from './ui/Button';
import Spinner from './ui/Spinner';

const FaceCamera = () => {
  const { videoRef, canvasRef, result, loading, error, startCamera, stopCamera, capture } =
    useFaceCamera();
  const { user } = useAuth();
  const [cameraStarted, setCameraStarted] = useState(false);
  const [checkinResult, setCheckinResult] = useState(null);
  const [recognitionResult, setRecognitionResult] = useState(null);

  useEffect(() => {
    return () => stopCamera();
  }, []);

  const handleStartCamera = async () => {
    await startCamera();
    setCameraStarted(true);
  };

  const handleCapture = async () => {
    try {
      const result = await capture();
      setRecognitionResult(result);
      setCheckinResult(null);
    } catch {
      console.error('Capture failed');
    }
  };

  const handleCheckIn = async () => {
    if (!recognitionResult?.recognized && !user?.id) return;
    try {
      const userId = recognitionResult?.recognized
        ? recognitionResult.user_id
        : user.id;
      const response = await attendanceService.checkIn(userId, 'FACE');
      setCheckinResult(response.data);
    } catch (err) {
      setCheckinResult({ error: err.response?.data?.detail || 'Check-in échoué' });
    }
  };

  return (
    <div className="space-y-6">
      <div className="relative bg-black rounded-xl overflow-hidden max-w-lg mx-auto">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="w-full h-auto"
        />
        <canvas ref={canvasRef} className="hidden" />
        {!cameraStarted && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-50">
            <Button onClick={handleStartCamera}>Démarrer la caméra</Button>
          </div>
        )}
      </div>

      <div className="flex justify-center gap-4">
        {cameraStarted && (
          <>
            <Button onClick={handleCapture} loading={loading} disabled={loading}>
              Capturer
            </Button>
            <Button variant="secondary" onClick={stopCamera}>
              Arrêter la caméra
            </Button>
          </>
        )}
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm text-center">
          {error}
        </div>
      )}

      {recognitionResult && (
        <div
          className={`rounded-xl p-6 text-center ${
            recognitionResult.recognized
              ? 'bg-green-50 border border-green-200'
              : 'bg-yellow-50 border border-yellow-200'
          }`}
        >
          {recognitionResult.recognized ? (
            <>
              <p className="text-lg font-semibold text-green-800">
                Bienvenue, {recognitionResult.user_name}
              </p>
              <p className="text-sm text-green-600 mt-1">
                Confiance : {((recognitionResult.confidence || 0) * 100).toFixed(1)}%
              </p>
              <Button className="mt-4" onClick={handleCheckIn}>
                Pointer ma présence
              </Button>
            </>
          ) : (
            <>
              <p className="text-lg text-yellow-800">{recognitionResult.message}</p>
              {user && (
                <Button className="mt-4" onClick={handleCheckIn}>
                  Pointer manuellement
                </Button>
              )}
            </>
          )}
        </div>
      )}

      {checkinResult && (
        <div
          className={`rounded-xl p-4 text-center ${
            checkinResult.error
              ? 'bg-red-50 text-red-700'
              : 'bg-green-50 text-green-700'
          }`}
        >
          {checkinResult.error || 'Pointage enregistré avec succès !'}
        </div>
      )}
    </div>
  );
};

export default FaceCamera;
