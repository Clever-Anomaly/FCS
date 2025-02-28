import { Link } from "react-router-dom";
import { useState } from "react";

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="bg-blue-600 p-4">
      <div className="container mx-auto flex justify-between items-center">
        {/* Logo */}
        <Link to="/" className="text-white text-2xl font-bold">
          MyApp
        </Link>

        {/* Mobile Menu Button */}
        <button
          className="text-white md:hidden"
          onClick={() => setIsOpen(!isOpen)}
        >
          ☰
        </button>

        {/* Links - Desktop */}
        <ul className="hidden md:flex space-x-6">
          <li><Link to="/" className="text-white hover:underline">Home</Link></li>
          <li><Link to="/about" className="text-white hover:underline">About</Link></li>
          <li><Link to="/logout" className="text-white hover:underline">Logout</Link></li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
