import { Routes, Route, Navigate } from "react-router-dom";
import AuthLayout from "./pages/auth/AuthLayout";
import Login from "./pages/auth/Login";
import Signup from "./pages/auth/Signup";
import RecoverPassword from "./pages/auth/RecoverPassword";
import ChangePassword from "./pages/auth/ChangePassword";
import ComponentGallery from "./pages/design/ComponentGallery";
import ShellDemo from "./pages/design/ShellDemo";
import { Toaster } from "./components/ui";

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/auth/login" replace />} />
        <Route path="/auth" element={<AuthLayout />}>
          <Route path="login" element={<Login />} />
          <Route path="signup" element={<Signup />} />
          <Route path="recover-password" element={<RecoverPassword />} />
          <Route path="change-password" element={<ChangePassword />} />
        </Route>
        <Route path="/design" element={<ComponentGallery />} />
        <Route path="/design/shell" element={<ShellDemo />} />
      </Routes>
      <Toaster />
    </>
  );
}
