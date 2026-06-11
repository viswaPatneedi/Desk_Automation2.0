import { Link } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '@store/slices/authSlice';

export default function Sidebar({ isOpen, onToggle }) {
  const dispatch = useDispatch();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: 'dashboard' },
    { path: '/devices', label: 'Devices', icon: 'devices' },
    { path: '/jobs', label: 'Jobs', icon: 'jobs' },
    { path: '/results', label: 'Results', icon: 'results' },
    { path: '/settings', label: 'Settings', icon: 'settings' },
  ];

  const handleLogout = () => {
    dispatch(logout());
  };

  return (
    <div className={`${isOpen ? 'w-64' : 'w-20'} bg-gray-900 text-white transition-all duration-300 hidden md:flex flex-col`}>
      {/* Logo */}
      <div className="p-4 border-b border-gray-800">
        <Link to="/" className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold">L</span>
          </div>
          {isOpen && <span className="font-bold text-sm">LRQA v2.0</span>}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className="px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-3"
          >
            <span className="w-6 h-6">{item.icon}</span>
            {isOpen && <span className="text-sm">{item.label}</span>}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <button
          onClick={handleLogout}
          className="w-full px-4 py-2 text-left text-sm rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-3"
        >
          <span className="w-6 h-6">🚪</span>
          {isOpen && <span>Logout</span>}
        </button>
      </div>
    </div>
  );
}
