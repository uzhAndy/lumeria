import NavigationBar from './NavigationBar'; // Adjust the import path as needed
import React from "react";
import type { ReactNode } from "react";

// Define the props interface for the Layout component
interface LayoutProps {
    children: ReactNode;
}

// Because navigationbar is fixed, make sure the children content only starts after the height of the navigationbar
const BaseLayout: React.FC<LayoutProps> = ({children}) => {
    return (
        <div>
            <NavigationBar/>
            <div className="pt-[60px]">
                {/*<div>*/}
                {children}
            </div>
        </div>
    );
};

export default BaseLayout;