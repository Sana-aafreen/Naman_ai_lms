const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// Basic health check route
app.get('/', (req, res) => {
    res.send('LMS Backend is running');
});

const sheetsRoutes = require('./routes/sheets');
const monitoringRoutes = require('./routes/monitoring');

app.use('/api', sheetsRoutes);
app.use('/api', monitoringRoutes);

app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
});
