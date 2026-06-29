import React, { useEffect, useState } from 'react';
import { useFaceCamera } from '../hooks/useFaceCamera';
import { attendanceService } from '../services/attendanceService';
import { useAuth } from '../hooks/useAuth';
import Button from './ui/Button';

const statusLabels = {
  present: { label: 'Présent', cls: 'bg-green-100 text-green-700' },
  late: { label: 'Retard', cls: 'bg-yellow-100 text-yellow-700' },
};

const FaceCamera = () => {
  const { videoRef, canvasRef, result: recognitionResult, loading, error, startCamera, stopCamera, capture } =
    useFaceCamera();
  const { user } = useAuth();

  const [cameraStarted, setCameraStarted] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionResult, setActionResult] = useState(null); // { status, time, name, error }

  useEffect(() => {
    return () => stopCamera();
  }, []);

  const handleStartCamera = async () => {
    await startCamera();
    setCameraStarted(true);
    setActionResult(null);
  };

  const handleCapture = async () => {
    setActionResult(null);
    await capture();
  };

  const doAction = async (type) => {
    const targetId = recognitionResult?.recognized ? recognitionResult.user_id : user?.id;
    const name = recognitionResult?.recognized ? recognitionResult.user_name : user?.full_name;
    if (!targetId) return;

    setActionLoading(true);
    try {
      let response;
      if (type === 'in') {
        response = await attendanceService.checkIn(targetId, recognitionResult?.recognized ? 'FACE' : 'MANUAL');
      } else {
        response = await attendanceService.checkOut(targetId);
      }
      setActionResult({
        name,
        type,
        status: response.data.status,
        time: response.data.check_in || response.data.check_out,
      });
    } catch (err) {
      setActionResult({ error: err.response?.data?.detail || 'Erreur lors du pointage' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleReset = () => {
    setActionResult(null);
  };

  return (
    <div className="space-y-6">
      {/* Camera viewport */}
      <div className="relative bg-gray-900 rounded-xl overflow-hidden max-w-lg mx-auto aspect-video flex items-center justify-center">
        <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />
        <canvas ref={canvasRef} className="hidden" />
        {!cameraStarted && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <p className="text-gray-400 text-sm">Caméra non démarrée</p>
            <Button onClick={handleStartCamera}>Démarrer la caméra</Button>
          </div>
        )}
      </div>

      {/* Controls */}
      {cameraStarted && !actionResult && (
        <div className="flex justify-center gap-4">
          <Button onClick={handleCapture} loading={loading} disabled={loading}>
            Capturer
          </Button>
          <Button variant="secondary" onClick={() => { stopCamera(); setCameraStarted(false); }}>
            Arrêter
          </Button>
        </div>
      )}

      {/* Camera or recognition error */}
      {error && !actionResult && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm text-center">
          {error}
        </div>
      )}

      {/* Recognition result → action panel */}
      {recognitionResult && !actionResult && (
        <div className={`rounded-xl p-6 space-y-4 border ${
          recognitionResult.recognized
            ? 'bg-green-50 border-green-200'
            : 'bg-yellow-50 border-yellow-200'
        }`}>
          {recognitionResult.recognized ? (
            <div className="text-center">
              <p className="text-lg font-semibold text-green-800">
                Bonjour, {recognitionResult.user_name}
              </p>
              <p className="text-sm text-green-600 mt-1">
                Confiance : {((recognitionResult.confidence || 0) * 100).toFixed(1)}%
              </p>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-yellow-800 font-medium">{recognitionResult.message}</p>
              {user && (
                <p className="text-sm text-yellow-600 mt-1">
                  Pointage manuel pour : <strong>{user.full_name}</strong>
                </p>
              )}
            </div>
          )}

          {/* Only show action buttons when there's a target user */}
          {(recognitionResult.recognized || user) && (
            <div className="flex justify-center gap-3 pt-2">
              <Button
                onClick={() => doAction('in')}
                loading={actionLoading}
                disabled={actionLoading}
              >
                Entrée
              </Button>
              <Button
                variant="secondary"
                onClick={() => doAction('out')}
                loading={actionLoading}
                disabled={actionLoading}
              >
                Sortie
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Post-action confirmation */}
      {actionResult && (
        <div className={`rounded-xl p-6 text-center space-y-3 border ${
          actionResult.error
            ? 'bg-red-50 border-red-200'
            : 'bg-green-50 border-green-200'
        }`}>
          {actionResult.error ? (
            <p className="text-red-700 font-medium">{actionResult.error}</p>
          ) : (
            <>
              <p className="text-gray-700 font-semibold text-lg">
                {actionResult.type === 'in' ? 'Entrée enregistrée' : 'Sortie enregistrée'}
              </p>
              {actionResult.name && (
                <p className="text-gray-600">{actionResult.name}</p>
              )}
              {actionResult.time && (
                <p className="text-gray-500 text-sm">
                  {new Date(actionResult.time).toLocaleTimeString('fr-FR')}
                </p>
              )}
              {actionResult.status && statusLabels[actionResult.status] && (
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${statusLabels[actionResult.status].cls}`}>
                  {statusLabels[actionResult.status].label}
                </span>
              )}
            </>
          )}
          <div className="pt-2">
            <Button variant="secondary" onClick={handleReset}>
              Nouveau pointage
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FaceCamera;
