const http = require('http');

const options = {
    hostname: 'localhost',
    port: 8000,
    path: '/api/',
    method: 'GET',
    agent: new http.Agent({ keepAlive: true, maxSockets: 500 }) // Keep-alive for max throughput
};

const CONCURRENCY = 300;
const DURATION_SEC = 5;

let completed = 0;
let errors = 0;
const startTime = Date.now();

console.log(`Starting Node.js Load Test: ${CONCURRENCY} connections for ${DURATION_SEC} seconds...`);

const runRequest = () => {
    if (Date.now() - startTime >= DURATION_SEC * 1000) return;

    const req = http.request(options, (res) => {
        // Discard the body quickly
        res.on('data', () => { });
        res.on('end', () => {
            if (res.statusCode === 200) {
                completed++;
            } else {
                errors++;
            }
            // Loop instantly
            runRequest();
        });
    });

    req.on('error', (e) => {
        errors++;
        runRequest();
    });

    req.end();
};

// Start initial batch
for (let i = 0; i < CONCURRENCY; i++) {
    runRequest();
}

// Check every second to see if we're done
const timer = setInterval(() => {
    if (Date.now() - startTime >= DURATION_SEC * 1000) {
        clearInterval(timer);
        const totalTime = (Date.now() - startTime) / 1000;
        const totalReqs = completed + errors;
        const rps = totalReqs / totalTime;

        console.log("\n==================================");
        console.log("🚀 LOAD TEST RESULTS");
        console.log("==================================");
        console.log(`Time Elapsed: ${totalTime.toFixed(2)}s`);
        console.log(`Total Requests: ${totalReqs}`);
        console.log(`Successful: ${completed}`);
        console.log(`Errors: ${errors}`);
        console.log(`Throughput: ${rps.toFixed(2)} Req/s`);
        console.log(`30-Min Extrapolation: ${(rps * 1800).toLocaleString('de-DE')} Updates`);
        console.log("==================================");
        process.exit(0);
    }
}, 1000);
