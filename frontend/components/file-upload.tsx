"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

export function FileUpload({ onUpload }: { onUpload: (file: File) => void }) {
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  return (
    <div className="space-y-3">
      <Label htmlFor="file" className="text-sm font-medium">
        Upload CSV
      </Label>
      <Input id="file" type="file" accept=".csv" onChange={handleFileChange} />
      <Button
        disabled={!file}
        onClick={() => file && onUpload(file)}
        className="w-full bg-blue-600 hover:bg-blue-700"
      >
        {file ? `Upload ${file.name}` : "Choose File"}
      </Button>
    </div>
  );
}
