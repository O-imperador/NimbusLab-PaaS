import { useState, useEffect } from 'react';
import { Terminal, Github, Server, Box, Moon, Sun, Loader } from 'lucide-react';
import { useTheme } from '../useTheme';

function DeployApp() {
  const { theme, toggleTheme } = useTheme();
  const [loading, setLoading] = useState(false);
  const [deploymentData, setDeploymentData] = useState(null);
  const [logs, setLogs] = useState([]);
  const [formData, setFormData] = useState({
    repo: '',
    type: 'LXC',
    framework: 'React'
  });
  const [appName, setAppName] = useState('');

const handleDeploy = async () => {
  setLoading(true);
  setLogs([]);
  setDeploymentData(null);
  const repoName = formData.repo.split('/').pop().replace('.git','');
  setAppName(repoName);

  try {
    await fetch('http://localhost:5000/deploy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData),
    });

    // Poll for logs every 2 seconds
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:5000/status/${repoName}`);
        const data = await res.json();
        setLogs(data.logs);

        // Check if deployment finished
        const finishedLine = data.logs.find(line => line.includes("Deployment completed"));
        if (finishedLine) {
          clearInterval(interval);
          // Extract URL from logs
          const accessLine = data.logs.find(l => l.includes("Access at"));
          const url = accessLine ? accessLine.split("Access at ")[1] : null;
          setDeploymentData({ status: "success", url, logs: data.logs });
          setLoading(false);
        }
      } catch (err) {
        console.error("Error polling logs:", err);
      }
    }, 2000);

  } catch (error) {
    console.error(error);
    setDeploymentData({ status: 'error', logs: ['Failed to connect to backend'] });
    setLoading(false);
  }
};


  return (
    <div className={`min-h-screen transition-colors duration-300`}>
      <div className="min-h-screen bg-gray-50 dark:bg-black text-gray-900 dark:text-gray-100 font-sans">
        {/* Header */}
        <nav className="border-b border-gray-200 dark:border-gray-800 px-6 py-4 flex justify-between items-center bg-white dark:bg-black">
          <div className="flex items-center gap-2 font-bold text-xl tracking-tighter">
            <div className="w-6 h-6 bg-black dark:bg-white rounded-full"></div>
            Nimbus Lab
          </div>
          <button onClick={toggleTheme} className="p-2 rounded-full transition-colors">
            {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
          </button>
        </nav>

        {/* Main Content */}
        <main className="max-w-4xl mx-auto mt-16 px-4">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-6xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Deploy in seconds.
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-lg">
              Import your Git repository and let our infrastructure handle the rest.
            </p>
          </div>

          {/* Deployment Card */}
          <div className="bg-white dark:bg-[#111] border border-gray-200 dark:border-gray-800 rounded-xl p-8 shadow-sm space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2 text-gray-600 dark:text-gray-400">Git Repository</label>
              <div className="relative">
                <Github className="absolute left-3 top-3 text-gray-400" size={20} />
                <input type="text" placeholder="https://github.com/username/repo"
                  className="w-full bg-gray-50 dark:bg-black border border-gray-200 dark:border-gray-800 rounded-lg py-3 pl-10 pr-4 focus:ring-2 focus:ring-blue-500 outline-none transition"
                  onChange={(e) => setFormData({...formData, repo: e.target.value})} />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-600 dark:text-gray-400">Infrastructure</label>
                <div className="flex gap-4">
                  {['LXC', 'VM'].map(type => (
                    <button key={type} onClick={() => setFormData({...formData, type})}
                      className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg border transition ${
                        formData.type === type ? 'bg-black text-white dark:bg-white dark:text-black border-transparent' : 'border-gray-200 dark:border-gray-800 hover:border-gray-400'
                      }`}>
                      {type === 'LXC' ? <Box size={18} /> : <Server size={18} />}
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-600 dark:text-gray-400">Framework</label>
                <select className="w-full bg-gray-50 dark:bg-black border border-gray-200 dark:border-gray-800 rounded-lg py-3 px-4 focus:ring-2 focus:ring-blue-500 outline-none appearance-none"
                  onChange={(e) => setFormData({...formData, framework: e.target.value})}>
                  <option>React</option>
                  <option>Node.js</option>
                  <option>Django</option>
                  <option>Flask</option>
                </select>
              </div>
            </div>

            <button onClick={handleDeploy} disabled={loading}
              className="w-full bg-black hover:bg-gray-800 dark:bg-white dark:hover:bg-gray-200 text-white dark:text-black font-bold py-4 rounded-lg transition-all transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2">
              {loading ? <Loader className="animate-spin" /> : 'Deploy Project'}
            </button>
          </div>

          {/* Logs */}
          {logs.length > 0 && (
            <div className="mt-8 p-6 rounded-xl border bg-black text-green-400 font-mono text-xs overflow-x-auto space-y-1">
              {logs.map((line, idx) => <div key={idx}>{line}</div>)}
            </div>
          )}

          {/* Deployment Result */}
          {deploymentData && deploymentData.status === "success" && (
            <div className="mt-8 p-6 rounded-xl border bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800">
              <div className="flex items-center gap-3 mb-4">
                <Terminal size={24} className='text-green-600' />
                <h3 className="text-lg font-bold">Deployment Completed</h3>
              </div>
              <div>
                <span className="text-gray-500">Access URL: </span>
                <a href={deploymentData.logs.find(l => l.includes("Access at")).split(" ")[-1]} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline">
                  {deploymentData.logs.find(l => l.includes("Access at")).split(" ")[-1]}
                </a>
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  )
}

export default DeployApp;
