import type { Metadata } from "next";
import localFont from "next/font/local";
import { Shell } from "@/components/shell";
import "./globals.css";
const manrope = localFont({
  src: "../../node_modules/@fontsource-variable/manrope/files/manrope-latin-wght-normal.woff2",
  display: "swap",
  variable: "--font-manrope",
});
export const metadata: Metadata = {
  title: {
    default: "Q-Compass · Portfolio research",
    template: "%s · Q-Compass",
  },
  description:
    "Local NIFTY portfolio experiments with classical and simulated quantum solvers.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={manrope.variable}>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
