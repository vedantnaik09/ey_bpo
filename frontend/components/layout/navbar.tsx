"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Phone, LogIn, ChevronDown } from "lucide-react";
import Link from "next/link";
import { auth } from "@/firebase/config";
import { onAuthStateChanged, signOut, User } from "firebase/auth";
import { usePathname } from "next/navigation";

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [userRole, setUserRole] = useState<string | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user);
      if (user) {
        const role = localStorage.getItem("userRole");
        setUserRole(role);
      } else {
        setUserRole(null);
      }
    });

    return () => {
      window.removeEventListener("scroll", handleScroll);
      unsubscribe();
    };
  }, []);

  const handleSignOut = async () => {
    await signOut(auth);
  };

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
          {userRole === "admin" && (
              <>
                <Link 
                  href="/dashboard" 
                  className={`text-sm font-medium transition-colors ${
                    pathname === "/dashboard"
                      ? "text-purple-600 dark:text-purple-400"
                      : "text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400"
                  }`}
                >
                  Dashboard
                </Link>

                <Link 
                      href="/admin/calls"
                      className={`text-sm font-medium transition-colors ${
                        pathname === "/admin/calls"
                          ? "text-purple-600 dark:text-purple-400"
                          : "text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400"
                      }`}
                    >
                      Calls
                </Link>

                {userRole === "admin" && (
                  <>
                    <Link 
                      href="/admin/users"
                      className={`text-sm font-medium transition-colors ${
                        pathname === "/admin/users"
                          ? "text-purple-600 dark:text-purple-400"
                          : "text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400"
                      }`}
                    >
                      Users
                      Employees

                    </Link>
                  </>
                )}
              </>
            )}

            {!user && (
              <>
                <Link href="/features" className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
                  Features
                </Link>
                <Link href="/pricing" className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
                  Pricing
                </Link>
                <Link href="/about" className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
                  About
                </Link>
              </>
            )}
          </div>

          <div className="flex-1 flex items-center justify-end gap-4">
            <Button variant="ghost" size="sm" className="hidden md:flex">
              <Phone className="mr-2 h-4 w-4" />
              <Link href={'/contact'} className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">Contact</Link>
            </Button>
            {user ? (
              <div className="relative">
                <button 
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className={`bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white border-0 flex items-center rounded-lg py-2 px-4 ${dropdownOpen?'rounded-b-none':''}`}
                >
                  {user.displayName}
                  <ChevronDown className="ml-2 h-4 w-4" />
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 border shadow-lg w-full py-1 bg-gradient-to-r rounded-b-sm font-bold">
                    <button
                      onClick={handleSignOut}
                      className="block w-full px-2 py-2 text-sm text-center text-gray-200 hover:text-white"
                    >
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link href="/auth">
                <Button 
                  size="sm"
                  className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white border-0"
                >
                  <LogIn className="mr-2 h-4 w-4" />
                  Login
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
