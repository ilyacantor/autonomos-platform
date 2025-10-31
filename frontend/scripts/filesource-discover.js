#!/usr/bin/env node
/**
 * FileSource Discovery CLI
 * Usage: npm run filesource:discover
 */

const http = require('http');

console.log('🔍 FileSource Discovery CLI\n');

const options = {
  hostname: 'localhost',
  port: 5000,
  path: '/api/v1/filesource/discover',
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  }
};

const req = http.request(options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    try {
      const response = JSON.parse(data);
      
      if (res.statusCode === 200) {
        console.log(`✅ Discovered ${response.files_count} CSV files\n`);
        
        if (response.files && response.files.length > 0) {
          console.log('📁 Files:');
          response.files.forEach(file => {
            console.log(`   ${file.filename}`);
            console.log(`      Entity: ${file.entity}`);
            console.log(`      System: ${file.system}`);
            console.log(`      Path: ${file.filepath}\n`);
          });
        } else {
          console.log('No files found in mock_sources/ directory');
        }
      } else {
        console.error(`❌ Discovery failed (${res.statusCode})`);
        console.error(response);
        process.exit(1);
      }
    } catch (e) {
      console.error('❌ Failed to parse response:', e.message);
      console.error('Raw response:', data);
      process.exit(1);
    }
  });
});

req.on('error', (error) => {
  console.error('❌ Request failed:', error.message);
  console.error('Make sure the API server is running on http://localhost:5000');
  process.exit(1);
});

req.end();
