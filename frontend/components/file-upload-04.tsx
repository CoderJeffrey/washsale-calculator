"use client";

import { File, FileSpreadsheet, X } from "lucide-react";
import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

type Props = {
  onUpload: (file: File) => Promise<void> | void; // 👈 parent-provided uploader
};

export default function FileUpload04({ onUpload }: Props) {
  const [uploadState, setUploadState] = useState<{
    file: File | null;
    progress: number;
    uploading: boolean;
  }>({ file: null, progress: 0, uploading: false });

  const fileInputRef = useRef<HTMLInputElement>(null);

  const validFileTypes = [
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ];

  const handleFile = (file: File | undefined) => {
    if (!file) return;

    if (validFileTypes.includes(file.type) || file.name.match(/\.(csv|xlsx|xls)$/i)) {
      setUploadState({ file, progress: 0, uploading: false }); // progress simulated during submit
    } else {
      toast.error("Please upload a CSV, XLSX, or XLS file.", { position: "bottom-right", duration: 3000 });
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    handleFile(event.target.files?.[0]);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    handleFile(event.dataTransfer.files?.[0]);
  };

  const resetFile = () => {
    setUploadState({ file: null, progress: 0, uploading: false });
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const getFileIcon = () => {
    if (!uploadState.file) return <File />;
    const fileExt = uploadState.file.name.split(".").pop()?.toLowerCase() || "";
    return ["csv", "xlsx", "xls"].includes(fileExt)
      ? <FileSpreadsheet className="h-5 w-5 text-foreground" />
      : <File className="h-5 w-5 text-foreground" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024; const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const { file, progress, uploading } = uploadState;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploadState((s) => ({ ...s, uploading: true, progress: 5 }));

    // simple simulated progress while uploading
    const timer = setInterval(() => {
      setUploadState((s) => ({ ...s, progress: Math.min(s.progress + 7, 85) }));
    }, 150);

    try {
      await onUpload(file); // 👈 parent does the actual POST
      clearInterval(timer);
      setUploadState((s) => ({ ...s, progress: 100, uploading: false }));
      toast.success("Upload complete");
    } catch (err: any) {
      clearInterval(timer);
      setUploadState((s) => ({ ...s, uploading: false, progress: 0 }));
      toast.error(err?.message || "Upload failed");
    }
  };

  return (
    <div className="flex items-center justify-center p-10 w-full max-w-lg">
      <form className="w-full" onSubmit={handleSubmit}>
        <div
          className="flex justify-center rounded-md border mt-2 border-dashed border-input px-6 py-12"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <div>
            <File className="mx-auto h-12 w-12 text-muted-foreground" aria-hidden />
            <div className="flex text-sm leading-6 text-muted-foreground">
              <p>Drag and drop or</p>
              <label
                htmlFor="file-upload-03"
                className="relative cursor-pointer rounded-sm pl-1 font-medium text-primary hover:underline hover:underline-offset-4"
              >
                <span>choose file</span>
                <input
                  id="file-upload-03"
                  name="file-upload-03"
                  type="file"
                  className="sr-only"
                  accept=".csv, .xlsx, .xls"
                  onChange={handleFileChange}
                  ref={fileInputRef}
                />
              </label>
              <p className="pl-1">to upload</p>
            </div>
          </div>
        </div>

        <p className="mt-2 text-xs leading-5 text-muted-foreground sm:flex sm:items-center sm:justify-between">
          <span>Accepted file types: CSV, XLSX or XLS files.</span>
          <span className="pl-1 sm:pl-0">Max. size: 10MB</span>
        </p>


        {file && (
          <Card className="relative mt-8 bg-muted p-4 gap-4">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1 h-8 w-8 text-muted-foreground hover:text-foreground"
              aria-label="Remove"
              onClick={resetFile}
            >
              <X className="h-5 w-5 shrink-0" aria-hidden />
            </Button>

            <div className="flex items-center space-x-2.5">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm bg-background shadow-sm ring-1 ring-inset ring-border">
                {getFileIcon()}
              </span>
              <div>
                <p className="text-xs font-medium text-foreground">{file?.name}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{file && formatFileSize(file.size)}</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Progress value={progress} className="h-1.5" />
              <span className="text-xs text-muted-foreground">{progress}%</span>
            </div>
          </Card>
        )}

        <div className="mt-8 flex items-center justify-end space-x-3">
          <Button type="button" variant="outline" className="whitespace-nowrap" onClick={resetFile} disabled={!file || uploading}>
            Cancel
          </Button>
          <Button type="submit" className="whitespace-nowrap" disabled={!file || uploading}>
            Upload
          </Button>
        </div>
      </form>
    </div>
  );
}
