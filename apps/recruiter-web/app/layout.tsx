import type { Metadata } from "next";
import "./globals.css";
import WorkspaceShell from "./components/WorkspaceShell";

export const metadata: Metadata = {
  title: "Medlivo Recruit AI",
  description: "Medlivo recruiter command center",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><WorkspaceShell>{children}</WorkspaceShell></body>
    </html>
  );
}
