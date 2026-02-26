import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const useDeltaPolling = (initialJobs, userRole) => {
    const [jobs, setJobs] = useState(initialJobs);
    const [lastServerNow, setLastServerNow] = useState(null);
    const consecutiveErrors = useRef(0);
    const isPolling = useRef(false);

    // Sync initial jobs when they arrive
    useEffect(() => {
        setJobs(initialJobs);
        if (!lastServerNow) {
            // Initialize lastServerNow if missing, subtracting 5 seconds to overlap safely
            const now = new Date();
            now.setSeconds(now.getSeconds() - 5);
            setLastServerNow(now.toISOString());
        }
    }, [initialJobs]);

    const fetchUpdates = useCallback(async () => {
        if (isPolling.current || !lastServerNow) return;

        // Check if tab is visible to avoid unnecessary polling
        if (document.visibilityState === 'hidden') return;

        try {
            isPolling.current = true;
            const res = await axios.get(`${API}/jobs/updates?since=${lastServerNow}`);

            const { serverNow, changedOrders } = res.data;

            if (changedOrders && changedOrders.length > 0) {
                setJobs(prevJobs => {
                    // Merge changed orders by replacing existing ones or appending new ones
                    const newJobsMap = new Map();

                    prevJobs.forEach(job => newJobsMap.set(job.id, job));
                    changedOrders.forEach(job => newJobsMap.set(job.id, job));

                    // Convert back to array (you can re-sort later if needed)
                    const mergedList = Array.from(newJobsMap.values());
                    // Keep newest updated first
                    mergedList.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

                    return mergedList;
                });
            }

            setLastServerNow(serverNow);
            consecutiveErrors.current = 0; // Reset errors

        } catch (error) {
            console.error('Polling error:', error);
            consecutiveErrors.current += 1;
        } finally {
            isPolling.current = false;
        }
    }, [lastServerNow]);

    useEffect(() => {
        // Backoff logic: 3s -> 6s -> 12s -> 20s
        let timeoutSeconds = 3;
        if (consecutiveErrors.current > 0) {
            timeoutSeconds = Math.min(3 * Math.pow(2, consecutiveErrors.current - 1), 20);
        }

        const interval = setInterval(() => {
            fetchUpdates();
        }, timeoutSeconds * 1000);

        return () => clearInterval(interval);
    }, [fetchUpdates]);

    // Handle manual refreshes gracefully
    const manualUpdate = (updatedJob) => {
        setJobs(prevJobs => {
            const newJobsMap = new Map();
            prevJobs.forEach(job => newJobsMap.set(job.id, job));
            newJobsMap.set(updatedJob.id, updatedJob);
            const mergedList = Array.from(newJobsMap.values());
            mergedList.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            return mergedList;
        });
    };

    return { jobs, setJobs, manualUpdate, lastServerNow, setLastServerNow };
};
