"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import axiosManagerInstance from "@/utils/axiosManager"
import { onAuthStateChanged } from "firebase/auth"
import { auth } from "@/firebase/config"
import { Loader2 } from "lucide-react"

interface User {
  user_id: string
  email: string
  role: string
  domain: string
}

const roles = ["admin", "employee"]
const domains = [
  "Technical Support",
  "Billing",
  "New Connection",
  "Added Service and Bundle offers",
]

export default function UsersPage() {
  const { push } = useRouter()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [editingUser, setEditingUser] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Partial<User>>({})

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (!user) {
        push("/")
      } else {
        const token = await user.getIdToken(true)
        localStorage.setItem("firebaseToken", token)
        const role = localStorage.getItem("userRole")
        if (role !== "admin") {
          push("/dashboard")
        }
        fetchUsers()
      }
    })

    return () => unsubscribe()
  }, [push])

  const fetchUsers = async () => {
    try {
      const response = await axiosManagerInstance.get("/users")
      setUsers(response.data)
    } catch (error) {
      toast.error("Failed to fetch users")
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateUser = async (user: User) => {
    try {
      const updateData = {
        email: editForm.email || user.email,
        role: editForm.role || user.role,
        domain: editForm.domain || user.domain,
      }
  
      console.log("Sending update request:", updateData) // Debugging log
  
      const response = await axiosManagerInstance.put(`/users/${user.email}`, updateData)
      
      console.log("Update response:", response.data) // Debugging log
      
      toast.success("User updated successfully")
      fetchUsers()
      setEditingUser(null)
      setEditForm({})
    } catch (error) {
      console.error("Update error:", error)
      toast.error("Failed to update user")
    }
  }
  

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900/50 pt-24 px-8 pb-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-6">User Management</h1>
          <Card className="bg-white dark:bg-gray-800">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Domain</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center">
                    <div className="flex items-center justify-center">
                      <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
                      <span className="ml-2">Loading users...</span>
                    </div>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-gray-900/50 pt-24 px-8 pb-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-6">User Management</h1>
        <Card className="bg-white dark:bg-gray-800">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Domain</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.user_id}>
                  <TableCell>
                    {editingUser === user.email ? (
                      <Input
                        value={editForm.email || user.email}
                        onChange={(e) =>
                          setEditForm({ ...editForm, email: e.target.value })
                        }
                      />
                    ) : (
                      user.email
                    )}
                  </TableCell>
                  <TableCell>
                    {editingUser === user.email ? (
                      <Select
                        value={editForm.role || user.role}
                        onValueChange={(value) =>
                          setEditForm({ ...editForm, role: value })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {roles.map((role) => (
                            <SelectItem key={role} value={role}>
                              {role}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      user.role
                    )}
                  </TableCell>
                  <TableCell>
                    {editingUser === user.email ? (
                      <Select
                        value={editForm.domain || user.domain}
                        onValueChange={(value) =>
                          setEditForm({ ...editForm, domain: value })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {domains.map((domain) => (
                            <SelectItem key={domain} value={domain}>
                              {domain}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      user.domain
                    )}
                  </TableCell>
                  <TableCell>
                    {editingUser === user.email ? (
                      <div className="gap-2 flex flex-center flex-wrap items-center">
                        <Button
                          variant="default"
                          onClick={() => handleUpdateUser(user)}
                        >
                          Save
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setEditingUser(null)
                            setEditForm({})
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <Button
                        variant="outline"
                        onClick={() => setEditingUser(user.email)}
                      >
                        Edit
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  )
}
