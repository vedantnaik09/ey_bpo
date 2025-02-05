"use client";

import { ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GradientText } from "@/components/ui/gradient-text";
import { BackgroundLines } from "@/components/ui/background-lines"
import { AnimatedFeatureBadge } from '@/components/ui/animated-badge'

export function Hero() {
  return (
    <section className="relative min-h-[90vh] flex items-center">
      {/* <BackgroundLines /> */}
      <div/>
      <div className="container mx-auto px-4 py-20">
        <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
          {/* <div className="flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-2 mb-8 border border-purple-100/20">
            <Sparkles className="h-4 w-4 text-purple-600" />
            <GradientText className="text-sm font-medium bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent animate-gradient">
              AI-Powered Call Management
            </GradientText>
          </div> */}
          <div className="mb-8">
            <AnimatedFeatureBadge />
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8">
            Transform Your BPO with{" "}
            <GradientText>Intelligent Automation</GradientText>
          </h1>
          
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-10 max-w-2xl">
            RESOLVR streamlines client interactions, automates scheduling, and
            enhances customer satisfaction through state-of-the-art AI assistance.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4">
            <Button size="lg" className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white border-0">
              Get Started Free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button size="lg" variant="outline" className="border-2">
              Schedule Demo
            </Button>
          </div>

          <div className="mt-16 p-6 bg-white/50 dark:bg-gray-900/50 backdrop-blur-sm rounded-2xl border border-purple-100/20">
            <p className="text-sm text-gray-600 dark:text-gray-400">Trusted by leading BPO companies</p>
            <div className="mt-4 flex justify-center gap-8">
              {/* Add company logos here */}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}