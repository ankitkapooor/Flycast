import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "../components/Navbar";
import { Footer } from "../components/Footer";

export const metadata: Metadata = {
  title: "FlyCast — Can a Fruit Fly Predict the Future?",
  description:
    "Run your time-series data through the complete MaleCNS fruit-fly connectome and see what an evolved biological network can predict.",
  keywords: [
    "Drosophila",
    "connectome",
    "reservoir computing",
    "time-series forecasting",
    "MaleCNS",
    "neuroscience",
    "machine learning",
  ],
  authors: [{ name: "FlyCast" }],
  openGraph: {
    title: "FlyCast — Can a Fruit Fly Predict the Future?",
    description:
      "Run your data through a real biological connectome. A computational reservoir using the complete MaleCNS Drosophila nervous system.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="flex min-h-full flex-col bg-background text-foreground bg-scientific-grid">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
