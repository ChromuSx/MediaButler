import { Heart, Coffee, DollarSign } from 'lucide-react';

const Footer = () => {
  // Support links configuration - can be overridden with environment variables
  const supportLinks = [
    {
      name: 'Buy Me a Coffee',
      url: import.meta.env.VITE_BUYMEACOFFEE_URL || 'https://buymeacoffee.com/chromus',
      icon: Coffee,
      color: 'hover:text-yellow-400',
      bgColor: 'hover:bg-yellow-400/10'
    },
    {
      name: 'Ko-fi',
      url: import.meta.env.VITE_KOFI_URL || 'https://ko-fi.com/chromus',
      icon: Heart,
      color: 'hover:text-red-400',
      bgColor: 'hover:bg-red-400/10'
    },
    {
      name: 'PayPal',
      url: import.meta.env.VITE_PAYPAL_URL || 'https://www.paypal.com/paypalme/giovanniguarino1999',
      icon: DollarSign,
      color: 'hover:text-blue-400',
      bgColor: 'hover:bg-blue-400/10'
    },
    {
      name: 'GitHub Sponsors',
      url: import.meta.env.VITE_GITHUB_SPONSORS_URL || 'https://github.com/sponsors/ChromuSx',
      icon: ({ className }) => (
        <svg className={className} viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
        </svg>
      ),
      color: 'hover:text-purple-400',
      bgColor: 'hover:bg-purple-400/10'
    }
  ];

  return (
    <footer className="bg-slate-800 border-t border-slate-700 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Support Message */}
          <div className="flex items-center gap-2 text-slate-400 text-sm">
            <Heart className="w-4 h-4 text-red-400" />
            <span>If you find MediaButler useful, consider supporting the project</span>
          </div>

          {/* Support Links */}
          <div className="flex items-center gap-3">
            {supportLinks.map((link) => {
              const Icon = link.icon;
              return (
                <a
                  key={link.name}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-700 text-slate-300 transition-all duration-200 ${link.color} ${link.bgColor} border border-slate-600 hover:border-slate-500 text-sm font-medium`}
                  title={`Support on ${link.name}`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{link.name}</span>
                </a>
              );
            })}
          </div>
        </div>

        {/* Copyright */}
        <div className="mt-4 pt-4 border-t border-slate-700 text-center text-xs text-slate-500">
          © {new Date().getFullYear()} MediaButler. Open source project.
        </div>
      </div>
    </footer>
  );
};

export default Footer;
