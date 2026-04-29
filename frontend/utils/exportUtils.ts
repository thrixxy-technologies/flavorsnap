/**
 * Utility functions for exporting data in different formats.
 */

export const exportToJSON = (data: any[], fileName: string) => {
  const jsonString = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonString], { type: "application/json" });
  downloadBlob(blob, `${fileName}.json`);
};

export const exportToCSV = (data: any[], fileName: string) => {
  if (data.length === 0) return;

  // Extract headers from keys of the first object
  const headers = Object.keys(data[0]);
  
  // Format rows
  const rows = data.map((item) => {
    return headers
      .map((header) => {
        const val = item[header];
        // Handle values that might contain commas
        const escaped = String(val).replace(/"/g, '""');
        return `"${escaped}"`;
      })
      .join(",");
  });

  const csvContent = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  downloadBlob(blob, `${fileName}.csv`);
};

const downloadBlob = (blob: Blob, fileName: string) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", fileName);
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
