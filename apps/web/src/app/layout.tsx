import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Verified Company Profile System",
  description:
    "Evidence-first company intelligence platform for AI Riser Vietnam",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
