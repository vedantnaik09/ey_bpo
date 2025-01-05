"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Phone, LogIn } from "lucide-react";
import Link from "next/link";

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? "bg-white/80 dark:bg-gray-950/80 backdrop-blur-md shadow-md" : "bg-transparent"
    }`}>
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16 md:h-20">
          <div className="flex-1">
            <Link href="/" className="text-xl md:text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              RESOLVR
            </Link>
          </div>

          <div className="flex-1 hidden md:flex items-center justify-center gap-8">
            <Link href="#features" className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
              Features
            </Link>
            <Link href="#pricing" className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
              Pricing
            </Link>
            <Link href="#about" className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
              About
            </Link>
          </div>

          <div className="flex-1 flex items-center justify-end gap-4">
            <Button variant="ghost" size="sm" className="hidden md:flex">
              <Phone className="mr-2 h-4 w-4" />
              Contact
            </Button>
            <Button 
              size="sm"
              className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white border-0"
            >
              <LogIn className="mr-2 h-4 w-4" />
              Login
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
}
