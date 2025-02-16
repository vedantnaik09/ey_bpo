"use client"

import { Sparkles } from "lucide-react"
import { motion } from "framer-motion"
import { GradientText } from "./gradient-text"

export function AnimatedFeatureBadge() {
  return (
    <motion.div
      className="flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-2 border border-purple-100/20 relative overflow-hidden cursor-pointer"
      animate={{ scale: [1, 1.05, 1] }}
      transition={{
        duration: 3,
        repeat: Number.POSITIVE_INFINITY,
        ease: "easeInOut",
      }}
      whileHover={{
        scale: 1.10,
        transition: {
          duration: 1.2,
          repeat: Number.POSITIVE_INFINITY,
          repeatType: "reverse",
        },
      }}
    >
      <Sparkles className="h-4 w-4 text-purple-600" />
      <motion.div
        className="text-sm font-medium bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent relative"
        animate={{
          backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"],
        }}
        transition={{
          duration: 5,
          repeat: Number.POSITIVE_INFINITY,
          ease: "linear",
        }}
      >
        <GradientText>AI-Powered Call Management</GradientText>
      </motion.div>
    </motion.div>
  )
}

