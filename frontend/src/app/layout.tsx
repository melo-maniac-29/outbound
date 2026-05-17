import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Outbound Nexus",
  description: "Outbound AI outreach pipeline dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
