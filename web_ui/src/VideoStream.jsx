import React, { useEffect, useRef, useState } from 'react';
import { PoseLandmarker, FilesetResolver, DrawingUtils } from "@mediapipe/tasks-vision";

import io from "socket.io-client";

const USE_GPU = true;
const MODEL_LITE_URI = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task" 
const MODEL_FULL_URI = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task" 
const MODEL_HEAVY_URI = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task" 
const MODEL_PATH = MODEL_LITE_URI;
const SMOOTH_LANDMARKS = true;
const SMOOTHING_FACTOR = 0.60;
const MAX_FPS = 30; // cap max FPS @TODO make configurable 

const smoothLandmarks = (currentLandmarks, prevSmoothedLandmarks) => {
    let smoothingFactor = SMOOTHING_FACTOR;

    if (prevSmoothedLandmarks.length === 0) {
        // Initial case, no smoothing needed
        return currentLandmarks;
    }

    // Smooth each landmark
    if (currentLandmarks) {
        const smoothedLandmarks = currentLandmarks.map((currentLandmark, i) => {
            const prevSmoothedLandmark = prevSmoothedLandmarks[i]
            return {
                x: (1 - smoothingFactor) * currentLandmark.x + smoothingFactor * prevSmoothedLandmark.x,
                y: (1 - smoothingFactor) * currentLandmark.y + smoothingFactor * prevSmoothedLandmark.y,
                z: (1 - smoothingFactor) * currentLandmark.z + smoothingFactor * prevSmoothedLandmark.z
            }
        });
        return smoothedLandmarks;
    } else {
        return currentLandmarks;
    }
}

const VideoStream = ({ handlePoseResults }) => {
    const videoRef = useRef();
    const canvasRef = useRef();
    const [keypointProcessingSpeed, setKeypointProcessingSpeed] = useState();
    
    useEffect(() => {
        let poseLandmarker;

        const initializePoseDetection = async () => {
            // For configuration options see
            // https://developers.google.com/mediapipe/solutions/vision/pose_landmarker/web_js
            try {
                const vision = await FilesetResolver.forVisionTasks(
                    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
                );
                poseLandmarker = await PoseLandmarker.createFromOptions(
                    vision, {
                    baseOptions: { 
                        modelAssetPath: MODEL_PATH, 
                        delegate: USE_GPU ? "GPU" : "CPU",
                    },
                    numPoses: 1,
                    runningMode: "VIDEO",
                    // minPoseDetectionConfidence: 0.90,
                    // minPosePresenceConfidence: 0.90,
                    // minTrackingConfidence: 0.90,
                });
                detectPose();
            } catch (error) {
                console.log("Error initializing pose landmark detection.", error)
            }
        };

        // For drawing keypoints
        const canvasElement = canvasRef.current;
        const video = videoRef.current;
        const canvasCtx = canvasElement.getContext("2d");
        const drawingUtils = new DrawingUtils(canvasCtx);
        let animationFrameId;
        let prevSmoothedLandmarks = [];
        const detectPose = () => {
            setTimeout(()=> {
                if (videoRef.current && videoRef.current.readyState >= 2) {
                    let startTimeMs = performance.now();
                    const start = performance.now(); // profile start
                    poseLandmarker.detectForVideo(videoRef.current, startTimeMs, (result) => {
                        if (SMOOTH_LANDMARKS) {
                            const smoothedLandmarks = smoothLandmarks(result.landmarks[0], prevSmoothedLandmarks);
                            prevSmoothedLandmarks = smoothedLandmarks;
                            const resultWithSmoothedLandmarks = {
                                ...result,
                                landmarks: [smoothedLandmarks]
                            };
                            result = resultWithSmoothedLandmarks;
                        }
                        handlePoseResults(result);
                        canvasElement.width = video.clientWidth;
                        canvasElement.height = video.clientHeight;
                        canvasCtx.save();
                        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
                        for (const landmark of result.landmarks) {
                          drawingUtils.drawLandmarks(landmark, {
                            radius: (data) => {
                                if (data) {
                                    DrawingUtils.lerp(data.from.z, -0.15, 0.1, 5, 1)
                                }
                            }
                          });
                          drawingUtils.drawConnectors(landmark, PoseLandmarker.POSE_CONNECTIONS);
                        }
                        canvasCtx.restore();
                    });
                    setKeypointProcessingSpeed(performance.now() - start); // profile end
                }
                requestAnimationFrame(detectPose);
            }, 1000 / MAX_FPS)
        }

        const startWebcam = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                videoRef.current.srcObject = stream;
                await initializePoseDetection();
            } catch (error) {
                console.error("Error accessing webcam:", error);
            }
        };

        startWebcam();

        return () => {
            if (videoRef.current && videoRef.current.srcObject) {
                videoRef.current.srcObject.getTracks().forEach(track => track.stop());
            }
            if (poseLandmarker) {
                poseLandmarker.close();
            }
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
            }
        }
    }, []);


    return (
        <div>
            <pre>
                Keypoint Processing Speed: {keypointProcessingSpeed}ms
            </pre>
            
            <div id="videoContainer">
                <video id="localVideo" ref={videoRef} autoPlay muted></video>
                <canvas id="videoStreamCanvas" ref={canvasRef} ></canvas>
            </div>
        </div>
    );
}
export default VideoStream;
