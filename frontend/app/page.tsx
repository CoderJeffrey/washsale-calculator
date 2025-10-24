"use client";

import { useState } from "react";
import { FileUpload } from "@/components/file-upload";
import FileUpload04 from "@/components/file-upload-04"; // adjust path to what the CLI created

interface WashSaleResult {
  Ticker: string;
  SellDate: string;
  Loss: number;
  DisallowedLoss: number;
  AdjustedBasisAddedTo: string;
}

export default function Home() {
  const [result, setResult] =
    useState<{ wash_sales: WashSaleResult[] | string } | null>(null);

  const handleUpload = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("http://127.0.0.1:8000/upload/", {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      setResult(data);
    } catch (error) {
      console.error("Upload error:", error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setResult({ wash_sales: `Upload failed: ${errorMessage}` });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background pb-[5vh]">
      <main className="w-full max-w-2xl mx-auto px-4">
        <div className="text-center space-y-8">
          <h1 className="text-4xl font-bold tracking-tight text-foreground">
            Wash Sale Calculator
          </h1>

          <div className="flex justify-center">
            <FileUpload04 onUpload={handleUpload} />
          </div>

          {result && (
            <div className="mt-10 text-left">
              <h3 className="text-xl font-medium mb-3 text-foreground">Results</h3>
              {typeof result.wash_sales === "string" ? (
                <p className="text-muted-foreground">{result.wash_sales}</p>
              ) : (
                <div className="overflow-hidden rounded-lg border">
                  <table className="min-w-full text-sm">
                    <thead className="bg-muted">
                      <tr>
                        <th className="p-3 text-left font-medium text-muted-foreground">Ticker</th>
                        <th className="p-3 text-left font-medium text-muted-foreground">SellDate</th>
                        <th className="p-3 text-left font-medium text-muted-foreground">Loss</th>
                        <th className="p-3 text-left font-medium text-muted-foreground">DisallowedLoss</th>
                        <th className="p-3 text-left font-medium text-muted-foreground">AdjustedBasisAddedTo</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {result.wash_sales.map((row, i) => (
                        <tr key={i} className="hover:bg-muted/50">
                          <td className="p-3 text-foreground">{row.Ticker}</td>
                          <td className="p-3 text-foreground">{row.SellDate}</td>
                          <td className="p-3 text-foreground">{row.Loss}</td>
                          <td className="p-3 text-foreground">{row.DisallowedLoss}</td>
                          <td className="p-3 text-foreground">{row.AdjustedBasisAddedTo}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
          {typeof result?.wash_sales !== "string" && result?.wash_sales?.length && (
            <div className="mt-8 p-4 bg-gray-50 rounded-lg border text-right">
              <p className="text-lg font-semibold text-gray-800">
                Total Disallowed Loss:&nbsp;
                <span className="text-red-600">
                  ${result?.wash_sales
                    ?.reduce((sum: number, row: any) => sum + row.DisallowedLoss, 0)
                    .toFixed(2)}
                </span>
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
