import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";

const stackSansNotch = localFont({
  src: "../fonts/static/StackSansNotch-Regular.ttf",
  variable: "--font-stack-sans-notch",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Wash Sale Calculator",
  description: "Detect and visualize wash-sale disallowed losses",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${stackSansNotch.variable} font-sans antialiased`} suppressHydrationWarning>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
