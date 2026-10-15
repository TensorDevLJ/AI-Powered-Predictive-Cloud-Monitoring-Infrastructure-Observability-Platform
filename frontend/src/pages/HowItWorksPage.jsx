import React from 'react';
import { motion } from 'framer-motion';
import {
    Cloud, Server, Activity, Database, Bell, Brain,
    ArrowRight, Monitor, Shield, BarChart3, Settings,
    CheckCircle, Cpu, HardDrive, Wifi, AlertTriangle, BookOpen
} from 'lucide-react';

const fadeIn = {
    hidden: { opacity: 0, y: 20 },
    visible: (i) => ({
        opacity: 1, y: 0,
        transition: { delay: i * 0.1, duration: 0.5 }
    })
};

const HowItWorksPage = () => {
    return (
        <div className="space-y-10 animate-in">
            {/* Page Header */}
            <div className="text-center">
                <h1 className="text-3xl font-bold gradient-text mb-2">How It Works</h1>
                <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                    Understand the complete workflow of the Cloud Monitoring System — from data collection to intelligent alerts.
                </p>
            </div>

            {/* Architecture Overview */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card p-6"
            >
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
                    <BookOpen className="w-5 h-5 text-primary-500" />
                    System Architecture
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center">
                    <ArchBlock icon={<Server />} label="EC2 Instance" sub="Node Exporter" color="blue" />
                    <ArrowBlock />
                    <ArchBlock icon={<Database />} label="Prometheus" sub="Metrics Store" color="orange" />
                    <ArrowBlock />
                    <ArchBlock icon={<Monitor />} label="FastAPI Backend" sub="API + ML Engine" color="purple" />
                </div>
                <div className="flex justify-center mt-4">
                    <div className="flex flex-col items-center">
                        <div className="w-0.5 h-8 bg-gray-300 dark:bg-gray-600"></div>
                        <ArrowDown />
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
                    <ArchBlock icon={<BarChart3 />} label="React Dashboard" sub="Visualization" color="green" />
                    <ArchBlock icon={<Bell />} label="Alertmanager" sub="Notifications" color="red" />
                    <ArchBlock icon={<BarChart3 />} label="Grafana" sub="Dashboards" color="yellow" />
                </div>
            </motion.div>

            {/* Workflow Steps */}
            <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-primary-500" />
                    Workflow Steps
                </h2>
                <div className="space-y-4">
                    {workflowSteps.map((step, i) => (
                        <motion.div
                            key={i}
                            custom={i}
                            initial="hidden"
                            animate="visible"
                            variants={fadeIn}
                            className="glass-card p-5 flex items-start gap-4"
                        >
                            <div className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center text-white bg-gradient-to-br ${step.gradient}`}>
                                <span className="text-sm font-bold">{i + 1}</span>
                            </div>
                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                    {step.icon}
                                    <h3 className="font-semibold text-gray-900 dark:text-white">{step.title}</h3>
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400">{step.description}</p>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>

            {/* Features Grid */}
            <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    Key Features
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {features.map((feat, i) => (
                        <motion.div
                            key={i}
                            custom={i}
                            initial="hidden"
                            animate="visible"
                            variants={fadeIn}
                            className="glass-card p-5"
                        >
                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white bg-gradient-to-br ${feat.gradient} mb-3`}>
                                {feat.icon}
                            </div>
                            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">{feat.title}</h3>
                            <p className="text-sm text-gray-600 dark:text-gray-400">{feat.description}</p>
                        </motion.div>
                    ))}
                </div>
            </div>

            {/* ML Features */}
            <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
                    <Brain className="w-5 h-5 text-purple-500" />
                    ML-Powered Features
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {mlFeatures.map((feat, i) => (
                        <motion.div
                            key={i}
                            custom={i}
                            initial="hidden"
                            animate="visible"
                            variants={fadeIn}
                            className="glass-card p-5 flex items-start gap-3"
                        >
                            <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                                <Brain className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-gray-900 dark:text-white text-sm">{feat.title}</h3>
                                <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">{feat.description}</p>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>

            {/* Quick Start Guide */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="glass-card p-6 bg-gradient-to-br from-primary-500/10 to-primary-600/5"
            >
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                    <Settings className="w-5 h-5 text-primary-500" />
                    Quick Start Guide
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {quickStart.map((step, i) => (
                        <div key={i} className="flex items-start gap-3">
                            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-500 text-white flex items-center justify-center text-sm font-bold">
                                {i + 1}
                            </div>
                            <div>
                                <h4 className="font-semibold text-sm text-gray-900 dark:text-white">{step.title}</h4>
                                <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">{step.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </motion.div>

            {/* API Endpoints Reference */}
            <div className="glass-card p-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                    <Cloud className="w-5 h-5 text-primary-500" />
                    API Endpoints
                </h2>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-gray-200 dark:border-gray-700">
                                <th className="p-3 text-left font-semibold text-gray-900 dark:text-white">Method</th>
                                <th className="p-3 text-left font-semibold text-gray-900 dark:text-white">Endpoint</th>
                                <th className="p-3 text-left font-semibold text-gray-900 dark:text-white">Description</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                            {apiEndpoints.map((ep, i) => (
                                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                                    <td className="p-3">
                                        <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${ep.method === 'GET' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                                ep.method === 'POST' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                                                    ep.method === 'PUT' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                                        'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                            }`}>
                                            {ep.method}
                                        </span>
                                    </td>
                                    <td className="p-3 font-mono text-xs text-gray-700 dark:text-gray-300">{ep.path}</td>
                                    <td className="p-3 text-gray-600 dark:text-gray-400">{ep.desc}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

/* --- Sub-components --- */

const ArchBlock = ({ icon, label, sub, color }) => {
    const colors = {
        blue: 'from-blue-500 to-blue-600',
        orange: 'from-orange-500 to-orange-600',
        purple: 'from-purple-500 to-purple-600',
        green: 'from-green-500 to-green-600',
        red: 'from-red-500 to-red-600',
        yellow: 'from-yellow-500 to-yellow-600',
    };
    return (
        <div className="flex flex-col items-center text-center p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white bg-gradient-to-br ${colors[color]} mb-2`}>
                {React.cloneElement(icon, { className: 'w-6 h-6' })}
            </div>
            <p className="font-semibold text-sm text-gray-900 dark:text-white">{label}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{sub}</p>
        </div>
    );
};

const ArrowBlock = () => (
    <div className="hidden md:flex items-center justify-center">
        <ArrowRight className="w-6 h-6 text-gray-400 dark:text-gray-500" />
    </div>
);

const ArrowDown = () => (
    <div className="flex items-center justify-center">
        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
    </div>
);

/* --- Data --- */

const workflowSteps = [
    {
        title: 'Data Collection',
        description: 'Node Exporter runs on your EC2 instance and exposes system metrics (CPU, memory, disk, network) on port 9100 as Prometheus-compatible endpoints.',
        icon: <Server className="w-4 h-4 text-blue-500" />,
        gradient: 'from-blue-500 to-blue-600'
    },
    {
        title: 'Metrics Scraping',
        description: 'Prometheus scrapes metrics from Node Exporter every 15 seconds and stores time-series data. It also evaluates alert rules for threshold violations.',
        icon: <Database className="w-4 h-4 text-orange-500" />,
        gradient: 'from-orange-500 to-orange-600'
    },
    {
        title: 'API Processing',
        description: 'FastAPI backend queries Prometheus via PromQL, processes raw metrics, and applies ML models for anomaly detection, predictions, and health scoring.',
        icon: <Brain className="w-4 h-4 text-purple-500" />,
        gradient: 'from-purple-500 to-purple-600'
    },
    {
        title: 'Real-time Dashboard',
        description: 'React frontend displays live metrics with auto-refresh every 15s. The dashboard shows CPU, memory, disk, and network usage with visual indicators.',
        icon: <Monitor className="w-4 h-4 text-green-500" />,
        gradient: 'from-green-500 to-green-600'
    },
    {
        title: 'Alerting',
        description: 'When metrics exceed thresholds (CPU > 80%, Memory > 85%, Disk > 90%), Alertmanager triggers notifications via email, Slack, or webhooks.',
        icon: <Bell className="w-4 h-4 text-red-500" />,
        gradient: 'from-red-500 to-red-600'
    },
    {
        title: 'Visualization',
        description: 'Grafana provides additional dashboards with historical data, custom panels, and advanced visualizations for deeper analysis.',
        icon: <BarChart3 className="w-4 h-4 text-yellow-500" />,
        gradient: 'from-yellow-500 to-yellow-600'
    },
];

const features = [
    { title: 'Real-time CPU Monitoring', description: 'Track CPU usage, per-core utilization, and load averages in real-time.', icon: <Cpu className="w-5 h-5" />, gradient: 'from-blue-500 to-blue-600' },
    { title: 'Memory Tracking', description: 'Monitor total, used, available memory, swap usage, and detect memory leaks.', icon: <HardDrive className="w-5 h-5" />, gradient: 'from-green-500 to-green-600' },
    { title: 'Disk Analytics', description: 'Track disk space, read/write bytes, and get capacity planning forecasts.', icon: <Database className="w-5 h-5" />, gradient: 'from-orange-500 to-orange-600' },
    { title: 'Network Monitoring', description: 'Monitor RX/TX bytes, packets, and network errors across all interfaces.', icon: <Wifi className="w-5 h-5" />, gradient: 'from-purple-500 to-purple-600' },
    { title: 'Smart Alerts', description: 'Configurable thresholds with email notifications and Alertmanager integration.', icon: <AlertTriangle className="w-5 h-5" />, gradient: 'from-red-500 to-red-600' },
    { title: 'JWT Authentication', description: 'Secure API access with token-based authentication and role-based access control.', icon: <Shield className="w-5 h-5" />, gradient: 'from-gray-600 to-gray-700' },
];

const mlFeatures = [
    { title: 'Anomaly Detection', description: 'Uses Isolation Forest and One-Class SVM to detect unusual system behavior.' },
    { title: 'CPU Prediction', description: 'RandomForest regression (lag + rolling-window features) forecasts CPU usage over the next 30+ minutes.' },
    { title: 'Memory Forecasting', description: 'RandomForest regression predicts memory trends; leak detection uses linear trend-slope analysis.' },
    { title: 'Health Scoring', description: 'Trained classifier predicts the probability of a near-term alert based on real historical alert outcomes, not a fixed formula.' },
    { title: 'Failure Prediction', description: 'Trained classifier predicts the probability of a critical alert in the near future, learned from real alert history.' },
    { title: 'Root Cause Analysis', description: 'A trained classifier (bootstrapped from rule-based diagnostics) identifies the primary causes of performance degradation.' },
    { title: 'Capacity Planning', description: '14–30 day resource forecasts using a trained day-level model, with trend-based fallback for new instances.' },
    { title: 'Auto-scaling Recommendations', description: 'Suggests when to scale up or down based on predicted resource needs.' },
];

const quickStart = [
    { title: 'Register & Login', desc: 'Create an account and log in to access the dashboard.' },
    { title: 'Add Instance', desc: 'Register your EC2 instance ID and IP address for monitoring.' },
    { title: 'View Metrics', desc: 'Check real-time CPU, memory, disk, and network data.' },
    { title: 'Configure Alerts', desc: 'Set thresholds and receive notifications when they are breached.' },
];

const apiEndpoints = [
    { method: 'POST', path: '/api/auth/register', desc: 'Register a new user' },
    { method: 'POST', path: '/api/auth/login', desc: 'Login and get JWT token' },
    { method: 'GET', path: '/api/auth/me', desc: 'Get current user profile' },
    { method: 'GET', path: '/api/instances/', desc: 'List all instances' },
    { method: 'GET', path: '/api/instances/{id}', desc: 'Get instance by ID or instance_id' },
    { method: 'POST', path: '/api/instances/', desc: 'Add a new instance' },
    { method: 'GET', path: '/api/metrics/cpu/{id}', desc: 'Get CPU metrics' },
    { method: 'GET', path: '/api/metrics/memory/{id}', desc: 'Get memory metrics' },
    { method: 'GET', path: '/api/metrics/disk/{id}', desc: 'Get disk metrics' },
    { method: 'GET', path: '/api/metrics/all/{id}', desc: 'Get all metrics combined' },
    { method: 'GET', path: '/api/ml/health-score/{id}', desc: 'Get ML health score' },
    { method: 'GET', path: '/api/ml/anomaly/detect/{id}', desc: 'Detect anomalies' },
    { method: 'GET', path: '/api/health', desc: 'System health check' },
];

export default HowItWorksPage;
