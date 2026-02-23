import { ReactNode } from 'react';
import { useTranslation } from 'next-i18next';
import Sidebar from './Sidebar';
import Footer from './Footer';

interface LayoutProps {
  children: ReactNode;
  title?: string;
  description?: string;
}

const Layout = ({ children, title = 'FlavorSnap', description }: LayoutProps) => {
  const { t } = useTranslation('common');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);
  const closeSidebar = () => setIsSidebarOpen(false);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile Header */}
      <header className="lg:hidden bg-white shadow-sm border-b border-gray-200 z-50">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center space-x-2">
            <button
              onClick={toggleSidebar}
              className="p-2 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
              aria-label="Toggle navigation menu"
              aria-expanded={isSidebarOpen}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <span className="text-xl font-bold text-accent">FlavorSnap 🍛</span>
          </div>
          
          {/* Language Switcher */}
          <div className="flex items-center">
            {/* Language switcher placeholder */}
          </div>
        </div>
      </header>

      {/* Desktop Header */}
      <header className="hidden lg:block bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-8">
              <span className="text-2xl font-bold text-accent">FlavorSnap 🍛</span>
              
              {/* Desktop Navigation */}
              <nav className="hidden md:flex space-x-4">
                <a 
                  href="/" 
                  className="text-accent font-medium focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded-md px-3 py-2 text-sm"
                >
                  Home
                </a>
                <a 
                  href="/about" 
                  className="text-gray-600 hover:text-accent transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded-md px-3 py-2 text-sm font-medium"
                >
                  About
                </a>
                <a 
                  href="/contact" 
                  className="text-gray-600 hover:text-accent transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded-md px-3 py-2 text-sm font-medium"
                >
                  Contact
                </a>
              </nav>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Language Switcher */}
              <div>
                {/* Language switcher placeholder */}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex">
        {/* Sidebar */}
        <Sidebar isOpen={isSidebarOpen} onClose={closeSidebar} />

        {/* Main Content */}
        <main className="flex-1 lg:ml-64">
          <div className="min-h-screen">
            {children}
          </div>
        </main>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default Layout;
