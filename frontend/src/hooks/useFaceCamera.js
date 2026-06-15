import { useState, useRef, useCallback } from 'react';
import { faceService } from '../services/faceService';

/**
 * Hook for managing webcam capture and face recognition.
 *
 * @returns {{ videoRef: object, canvasRef: object, result: object|null, loading: boolean, error: string|null, startCamera: Function, stopCamera: Function, capture: Function }}
 */
export const useFaceCamera = () => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const startCamera = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      setError('Camera access denied: ' + err.message);
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const capture = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const blob = await new Promise((resolve) =>
        canvas.toBlob(resolve, 'image/jpeg', 0.9)
      );
      const formData = new FormData();
      formData.append('file', blob, 'capture.jpg');
      const response = await faceService.recognize(formData);
      setResult(response.data);
      return response.data;
    } catch (err) {
      const msg = err.response?.data?.detail || 'Recognition failed';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  return { videoRef, canvasRef, result, loading, error, startCamera, stopCamera, capture };
};
