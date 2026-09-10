import './App.css'
import {BrowserRouter as Router, Routes, Route} from "react-router-dom";
import Dashboard from "./containers/Dashboard/Dashboard.tsx";
import BaseLayout from "./components/BaseLayout.tsx";
import FaqManagementPage from "./containers/FaqManagementPage.tsx";
import AboutPage from "./containers/AboutPage.tsx";

function App() {

    return (
        <Router>
            <Routes>
                {/* Default route */}
                <Route
                    path="/"
                    element={
                        <BaseLayout>
                            <Dashboard />
                        </BaseLayout>
                    }
                />
                <Route
                    path="/dashboard"
                    element={
                        <BaseLayout>
                            <Dashboard/>
                        </BaseLayout>
                    }/>
                <Route
                    path="/faq-management/:campaignId"
                    element={
                        <BaseLayout>
                            <FaqManagementPage />
                        </BaseLayout>
                    }
                />
                <Route
                    path="/about"
                    element={
                        <BaseLayout>
                            <AboutPage />
                        </BaseLayout>
                    }
                />
            </Routes>
        </Router>
    )
}

export default App
