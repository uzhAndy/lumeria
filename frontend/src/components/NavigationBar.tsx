import * as NavigationMenu from "@radix-ui/react-navigation-menu";
import "./BaseLayout.css";

const NavigationBar = () => {
    return (
        <NavigationMenu.Root className="navbar-custom">
            {/* Logo */}
            <div className="text-xl pr-10 font-bold text-blue-50">Lumeria</div>

            {/* Navigation Links */}
            <NavigationMenu.List className="flex space-x-4">
                <NavigationMenu.Item>
                    <NavigationMenu.Link
                        href="/dashboard"
                        className="pr-3"
                    >
                        Dashboard
                    </NavigationMenu.Link>
                </NavigationMenu.Item>

                <NavigationMenu.Item>
                    <NavigationMenu.Link
                        href="/about"
                        className="pr-3"
                    >
                        About
                    </NavigationMenu.Link>
                </NavigationMenu.Item>
            </NavigationMenu.List>
        </NavigationMenu.Root>
    );
};

export default NavigationBar;

