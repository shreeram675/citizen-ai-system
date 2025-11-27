import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, CheckCircle, AlertCircle } from 'lucide-react';
import Navbar from '../../components/shared/Navbar';
import Card from '../../components/shared/Card';
import Badge from '../../components/shared/Badge';
import Button from '../../components/shared/Button';
import './OfficerDashboard.css';

const MOCK_REPORTS = [
    { id: 1, title: 'Pothole on Main Street', category: 'Roads', status: 'Pending', priority: 'High', assignedDate: '2023-11-20' },
    { id: 2, title: 'Street Light Not Working', category: 'Electricity', status: 'In Progress', priority: 'Medium', assignedDate: '2023-11-19' },
    { id: 3, title: 'Broken Water Pipe', category: 'Water', status: 'Pending', priority: 'High', assignedDate: '2023-11-21' },
    { id: 4, title: 'Traffic Signal Malfunction', category: 'Roads', status: 'In Progress', priority: 'Critical', assignedDate: '2023-11-18' }
];

const OfficerDashboard = () => {
    const navigate = useNavigate();
    const [filter, setFilter] = useState('all');

    const stats = {
        pending: MOCK_REPORTS.filter(r => r.status === 'Pending').length,
        inProgress: MOCK_REPORTS.filter(r => r.status === 'In Progress').length,
        resolved: 8
    };

    const getStatusVariant = (status) => {
        switch (status.toLowerCase()) {
            case 'resolved': return 'success';
            case 'in progress': return 'warning';
            case 'pending': return 'danger';
            default: return 'neutral';
        }
    };

    const getPriorityVariant = (priority) => {
        switch (priority.toLowerCase()) {
            case 'critical': return 'danger';
            case 'high': return 'warning';
            case 'medium': return 'info';
            default: return 'neutral';
        }
    };

    const filteredReports = filter === 'all'
        ? MOCK_REPORTS
        : MOCK_REPORTS.filter(r => r.status.toLowerCase().replace(' ', '') === filter);

    return (
        <div className="min-h-screen bg-background">
            <Navbar />

            <main className="container py-lg">
                <div className="dashboard-header">
                    <div>
                        <h1 className="text-2xl mb-xs">Officer Dashboard</h1>
                        <p className="text-muted">Manage assigned reports and update their status</p>
                    </div>
                </div>

                <div className="stats-grid">
                    <Card className="stat-card">
                        <div className="stat-icon pending">
                            <Clock size={24} />
                        </div>
                        <div className="stat-content">
                            <p className="stat-label">Pending</p>
                            <p className="stat-value">{stats.pending}</p>
                        </div>
                    </Card>

                    <Card className="stat-card">
                        <div className="stat-icon in-progress">
                            <AlertCircle size={24} />
                        </div>
                        <div className="stat-content">
                            <p className="stat-label">In Progress</p>
                            <p className="stat-value">{stats.inProgress}</p>
                        </div>
                    </Card>

                    <Card className="stat-card">
                        <div className="stat-icon resolved">
                            <CheckCircle size={24} />
                        </div>
                        <div className="stat-content">
                            <p className="stat-label">Resolved</p>
                            <p className="stat-value">{stats.resolved}</p>
                        </div>
                    </Card>
                </div>

                <Card className="mt-lg">
                    <div className="flex justify-between items-center mb-md flex-wrap gap-md">
                        <h2 className="text-xl">Assigned Reports</h2>
                        <div className="filter-tabs">
                            <button
                                className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
                                onClick={() => setFilter('all')}
                            >
                                All
                            </button>
                            <button
                                className={`filter-tab ${filter === 'pending' ? 'active' : ''}`}
                                onClick={() => setFilter('pending')}
                            >
                                Pending
                            </button>
                            <button
                                className={`filter-tab ${filter === 'inprogress' ? 'active' : ''}`}
                                onClick={() => setFilter('inprogress')}
                            >
                                In Progress
                            </button>
                        </div>
                    </div>

                    <div className="reports-table-container">
                        <table className="reports-table">
                            <thead>
                                <tr>
                                    <th>Title</th>
                                    <th>Category</th>
                                    <th>Priority</th>
                                    <th>Status</th>
                                    <th>Assigned Date</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredReports.map(report => (
                                    <tr key={report.id}>
                                        <td className="font-semibold">{report.title}</td>
                                        <td>{report.category}</td>
                                        <td>
                                            <Badge variant={getPriorityVariant(report.priority)}>
                                                {report.priority}
                                            </Badge>
                                        </td>
                                        <td>
                                            <Badge variant={getStatusVariant(report.status)}>
                                                {report.status}
                                            </Badge>
                                        </td>
                                        <td>{new Date(report.assignedDate).toLocaleDateString()}</td>
                                        <td>
                                            <Button
                                                size="sm"
                                                onClick={() => navigate(`/officer/report/${report.id}`)}
                                            >
                                                Manage
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            </main>
        </div>
    );
};

export default OfficerDashboard;
