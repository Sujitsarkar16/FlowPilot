import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PulseOS | Life Feed",
  description: "A safety-first personal automation control centre.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
