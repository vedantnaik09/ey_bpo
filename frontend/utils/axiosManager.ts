import axios from "axios";
import { auth } from "@/firebase/config";

const axiosManagerInstance = axios.create({
    baseURL: "http://localhost:8000",
});

axiosManagerInstance.interceptors.request.use(
    async (config) => {
        // Get current user
        const user = auth.currentUser;
        if (user) {
            // Get fresh token
            const token = await user.getIdToken(true);
            // Store the fresh token
            localStorage.setItem("firebaseToken", token);
            // Add to request header
            config.headers = config.headers || {};
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add response interceptor to handle 401 errors
axiosManagerInstance.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Redirect to login page
            window.location.href = "/";
        }
        return Promise.reject(error);
    }
);

export default axiosManagerInstance;