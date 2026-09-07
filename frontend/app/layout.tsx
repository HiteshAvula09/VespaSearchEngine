import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "VespaSearch",
  description: "Enterprise hybrid search and grounded RAG"
};

export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
