"use client";

import { useState } from "react";

interface WashSaleResult {
  Ticker: string;
  SellDate: string;
  Loss: number;
  DisallowedLoss: number;
  AdjustedBasisAddedTo: string;
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<{ wash_sales: WashSaleResult[] | string } | null>(null);

  const handleUpload = async () => {
    if (!file) {
      alert("Please select a CSV file first");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/upload/", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    }
  };

  return (
    <main style={{ maxWidth: 600, margin: "2rem auto", textAlign: "center" }}>
      <h2>Wash Sale Calculator</h2>
      <input
        type="file"
        accept=".csv"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <button
        onClick={handleUpload}
        style={{ marginLeft: "1rem", padding: "0.5rem 1rem" }}
      >
        Upload
      </button>

      {result && (
        <div style={{ marginTop: "2rem", textAlign: "left" }}>
          <h3>Results</h3>
          {typeof result.wash_sales === "string" ? (
            <p>{result.wash_sales}</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>SellDate</th>
                  <th>Loss</th>
                  <th>DisallowedLoss</th>
                  <th>AdjustedBasisAddedTo</th>
                </tr>
              </thead>
              <tbody>
                {result.wash_sales.map((row, i) => (
                  <tr key={i}>
                    <td>{row.Ticker}</td>
                    <td>{row.SellDate}</td>
                    <td>{row.Loss}</td>
                    <td>{row.DisallowedLoss}</td>
                    <td>{row.AdjustedBasisAddedTo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </main>
  );
}
