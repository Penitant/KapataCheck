import { useCallback, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";
import fileSvg from '../assets/file.svg'
import { useResults } from '../context/ResultsContext'
import { motion } from 'framer-motion'
import { softScale, fadeInUp } from './motionPresets'

export function UploaderSection() {
  const [progress, setProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const { storePayload } = useResults()

  // List of accepted file types
  const acceptedFileTypes = useMemo(() => [
    "application/pdf",                                           // pdf
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", // docx
    "text/plain",                                                // txt
    "text/markdown",                                             // md
    "text/csv"                                                   // csv
  ], []);

  const onDrop = useCallback((acceptedFiles) => {
    // Validate file count (min only)
    if (acceptedFiles.length < 2) {
      setError("Please upload at least 2 EoI documents for comparison");
      return;
    }

    // Validate file types
    const invalidFiles = acceptedFiles.filter(
      file => !acceptedFileTypes.includes(file.type)
    );
    
    if (invalidFiles.length > 0) {
      setError(`Invalid file type(s): ${invalidFiles.map(f => f.name).join(', ')}. Please upload PDF, DOCX, TXT, MD, or CSV files only.`);
      return;
    }

    setError(null);
    setSuccessMessage(null);
    setProgress(0);
    setIsProcessing(true);
    setUploadedFiles(acceptedFiles.map(file => ({
      name: file.name,
      size: file.size,
      type: file.type
    })));

    // Prepare form data
    const formData = new FormData();
    acceptedFiles.forEach(file => {
      formData.append("files", file);
    });

    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

    // Upload documents for analysis
    axios.post(`${apiBaseUrl}/verify`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      responseType: 'json',
      onUploadProgress: (e) => {
        const percent = Math.round((e.loaded * 100) / e.total);
        setProgress(percent);
      }
    })
  .then(res => {
      setIsProcessing(false);
      setProgress(100);
      // Store results globally and remain on landing page (no auto-navigation)
      if (res?.data) {
    storePayload(res.data)
    // The results table below the uploader will animate in with the new data
      } else {
        setSuccessMessage(`Successfully uploaded ${acceptedFiles.length} EoI documents for similarity analysis`);
      }
    })
    .catch(async (err) => {
      console.error("Upload error:", err);
      setIsProcessing(false);
      setProgress(0);
      let errorMessage = "Error uploading documents. Please try again.";
      if (err.response?.data) {
        if (typeof err.response.data === 'object' && err.response.data.detail) {
          errorMessage = err.response.data.detail;
        } else if (typeof err.response.data === 'object' && err.response.data.error) {
          errorMessage = err.response.data.error;
        }
      }
      setError(errorMessage);
    });
  }, [acceptedFileTypes, storePayload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
      "text/markdown": [".md"],
      "text/csv": [".csv"]
    },
    multiple: true
  });

  const resetUpload = () => {
    setProgress(0);
    setIsProcessing(false);
    setUploadedFiles([]);
    setError(null);
    setSuccessMessage(null);
  };

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <div className="flex flex-col items-center space-y-6">
        <motion.div
          {...getRootProps()}
          className={`
            text-center rounded-2xl h-64 w-full max-w-2xl
            flex flex-col items-center justify-center 
            cursor-pointer transition-all duration-300
            backdrop-blur-2xl bg-white/2 border border-white/5
            ${isDragActive 
              ? 'scale-105 bg-white/4' 
              : 'hover:bg-white/3'
            }
            ${isProcessing ? 'cursor-not-allowed opacity-75' : ''}
          `}
          initial={softScale.initial}
          animate={softScale.animate}
          transition={softScale.transition}
        >
          <input {...getInputProps()} disabled={isProcessing} />
          
          {isProcessing ? (
            <div className="flex flex-col items-center space-y-4">
              <div className="text-white text-xl font-semibold">Uploading documents...</div>
              <div className="w-64 bg-white/20 rounded-full h-3 overflow-hidden">
                <motion.div 
                  className="bg-white h-3 rounded-full"
                  style={{ width: `${progress}%` }}
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ type: 'tween', duration: 0.2 }}
                />
              </div>
              <div className="text-sm text-white font-medium">{progress}% complete</div>
              <div className="text-xs text-white/80">
                Uploading {uploadedFiles.length} files
              </div>
            </div>
          ) : isDragActive ? (
            <motion.div className="text-white text-xl font-semibold" variants={fadeInUp} initial="initial" animate="animate" transition={fadeInUp.transition}>
              Drop your EoI documents here...
            </motion.div>
          ) : (
            <div className="flex flex-col items-center space-y-3">
              <motion.img src={fileSvg} alt="File Icon" className="w-12 h-12 brightness-0 invert" {...softScale} />
              <motion.div className="text-lg font-semibold text-white" variants={fadeInUp} initial="initial" animate="animate">Drag & drop EoI documents here</motion.div>
              <motion.div className="text-sm text-white/80" variants={fadeInUp} initial="initial" animate="animate" transition={{ delay: 0.05 }}>or click to select files</motion.div>
              <motion.div className="text-xs text-white/60 mt-2" variants={fadeInUp} initial="initial" animate="animate" transition={{ delay: 0.1 }}>
                Upload 2+ Company Profiles or Past Experience documents
              </motion.div>
              <motion.div className="text-xs text-white/60" variants={fadeInUp} initial="initial" animate="animate" transition={{ delay: 0.15 }}>
                Supported formats: PDF, DOCX, TXT, MD, CSV | Max size: 25MB each
              </motion.div>
            </div>
          )}
        </motion.div>

        {error && (
          <motion.div className="text-white p-4 max-w-2xl w-full text-center" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <div className="font-semibold">❌ Error</div>
            <div className="mt-1">{error}</div>
            <motion.button 
              onClick={resetUpload}
              className="mt-3 px-4 py-2 border border-white/40 text-white rounded-lg hover:border-white/60 hover:bg-white/10 transition-colors"
              whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}
            >
              Try Again
            </motion.button>
          </motion.div>
        )}

        {successMessage && (
          <motion.div className="text-white p-4 max-w-2xl w-full text-center" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <div className="font-semibold">✅ Success</div>
            <div className="mt-1">{successMessage}</div>
            
            {uploadedFiles.length > 0 && (
              <div className="mt-3 text-left border border-white/20 p-3 rounded-lg max-h-48 overflow-y-auto">
                <div className="text-sm font-medium mb-2 text-white">Uploaded files</div>
                <ul className="text-xs space-y-1 text-white/80">
                  {uploadedFiles.map((file, index) => (
                    <li key={index} className="flex justify-between">
                      <span className="truncate max-w-xs">{file.name}</span>
                      <span className="text-white/60">
                        {(file.size / 1024).toFixed(1)} KB
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            <motion.button 
              onClick={resetUpload}
              className="mt-3 px-6 py-2 border border-white/40 text-white rounded-lg hover:border-white/60 hover:bg-white/10 transition-colors font-medium"
              whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}
            >
              Upload More Documents
            </motion.button>
          </motion.div>
        )}
      </div>
    </div>
  );

}