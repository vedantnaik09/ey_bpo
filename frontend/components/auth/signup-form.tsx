"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createUserWithEmailAndPassword, updateProfile, signInWithPopup } from "firebase/auth";
import { auth, googleProvider } from "@/firebase/config";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Icons } from "@/components/icons";
import axios from "axios";

interface FormElements extends HTMLFormControlsCollection {
  email: HTMLInputElement;
  password: HTMLInputElement;
  name: HTMLInputElement;
}

interface SignUpFormElement extends HTMLFormElement {
  readonly elements: FormElements;
}

export function SignUpForm() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { push } = useRouter();

  async function onSubmit(event: React.FormEvent<SignUpFormElement>) {
    event.preventDefault();
    setIsLoading(true);

    const { email, password, name } = event.currentTarget.elements;

    try {
      // 1. Create user in Firebase
      const userCredential = await createUserWithEmailAndPassword(auth, email.value, password.value);
      // 2. Set the displayName in Firebase profile
      await updateProfile(userCredential.user, { displayName: name.value });
      // 3. Get the ID token to pass to your backend
      const token = await userCredential.user.getIdToken();
      localStorage.setItem("firebaseToken", token); // Add this line before the axios call

      // 4. Send token to Python backend using axios
      const response = await axios.post("http://localhost:8000/auth", { token }, {
        headers: { "Content-Type": "application/json" }
      });
      const data = response.data;

      // Store email, role, and domain in local storage
      localStorage.setItem("userEmail", data.email);
      localStorage.setItem("userRole", data.role);
      localStorage.setItem("userDomain", data.domain);

      console.log("User details:", userCredential.user);
      // 5. Redirect or do other client-side logic
      push("/dashboard");
    } catch (error) {
      const firebaseError = error as { message: string };
      setError(firebaseError.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleGoogleSignIn() {
    setIsLoading(true);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;
      // Get token
      const token = await user.getIdToken();
      localStorage.setItem("firebaseToken", token); // Add this line before the axios call

      // Send token to Python backend using axios
      const response = await axios.post("http://localhost:8000/auth", { token }, {
        headers: { "Content-Type": "application/json" }
      });
      const data = response.data;

      // Store email, role, and domain in local storage
      localStorage.setItem("userEmail", data.email);
      localStorage.setItem("userRole", data.role.trim());
      localStorage.setItem("userDomain", data.domain);

      console.log("User details:", user);
      push("/dashboard");
    } catch (error) {
      const firebaseError = error as { message: string };
      setError(firebaseError.message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">Full Name</Label>
          <Input id="name" name="name" placeholder="John Doe" type="text" required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" name="email" placeholder="name@example.com" type="email" required />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" name="password" type="password" required />
        </div>
        {error && <p className="text-red-500">{error}</p>}
        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading && <Icons.spinner className="mr-2 h-4 w-4 animate-spin" />}
          Create Account
        </Button>
      </form>

      <div className="text-center">or</div>
      <div className="w-full text-center">
        <button
          onClick={handleGoogleSignIn}
          type="button"
          disabled={isLoading}
          className="login-with-google-btn w-[1/2] mx-auto rounded-xl"
        >
          Sign in with Google
        </button>
      </div>
    </div>
  );
}