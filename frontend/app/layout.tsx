import type { Metadata } from "next";
import { Space_Grotesk, Open_Sans } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space",
  subsets: ["latin"],
});

const openSans = Open_Sans({
  variable: "--font-open",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FraudLens - Ops Intelligence",
  description: "Enterprise Fraud Investigation Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${spaceGrotesk.variable} ${openSans.variable} antialiased bg-background text-foreground flex min-h-screen font-sans`}
      >
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0 overflow-x-hidden">
          {children}
        </main>
      </body>
    </html>
  );
}
