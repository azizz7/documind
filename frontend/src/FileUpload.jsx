import { useState, useRef } from "react";

export default function FileUpload({ apiBase, onUploadSuccess }) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [statusMessage, setStatusMessage] = useState("");
  const fileInputRef = useRef(null);

  const uploadFile = async (file) => {
    if (!file.name.endsWith(".pdf")) {
      setUploadStatus("error");
      setStatusMessage("Please upload a PDF file.");
      return;
    }

    setUploading(true);
    setUploadStatus(null);
    setStatusMessage("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${apiBase}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Upload failed");
      }

      setUploading(false);
      onUploadSuccess();
    } catch (error) {
      setUploadStatus("error");
      setStatusMessage(error.message);
      setUploading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files[0];
    if (file) uploadFile(file);
  };

  return (
    <div className="file-upload">
      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""} ${uploading ? "uploading" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload PDF"
      >
        {uploading ? (
          <>
            <p>Uploading...</p>
            <div className="upload-progress-container">
              <div className="upload-progress-bar" />
            </div>
          </>
        ) : (
          <p>Click or drag to upload</p>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        style={{ display: "none" }}
        onChange={handleFileInputChange}
      />

      {uploadStatus === "error" && (
        <div className="upload-status error">
          ✗ {statusMessage}
        </div>
      )}
    </div>
  );
}
