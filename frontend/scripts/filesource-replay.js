#!/usr/bin/env node
/**
 * FileSource Replay CLI
 * Usage: npm run filesource:replay [-- --entity=account] [--system=salesforce]
 */

const http = require('http');

const args = process.argv.slice(2);
let entity = null;
let system = null;
let tenant = 'demo-tenant';

args.forEach(arg => {
  if (arg.startsWith('--entity=')) {
    entity = arg.split('=')[1];
  } else if (arg.startsWith('--system=')) {
    system = arg.split('=')[1];
  } else if (arg.startsWith('--tenant=')) {
    tenant = arg.split('=')[1];
  } else if (arg === '--all') {
    entity = null;
    system = null;
  }
});

const queryParams = new URLSearchParams();
if (entity) queryParams.append('entity', entity);
if (system) queryParams.append('system', system);
queryParams.append('tenant_id', tenant);

const path = `/api/v1/filesource/replay?${queryParams.toString()}`;

console.log('🔄 FileSource Replay CLI');
console.log(`   Entity: ${entity || 'all'}`);
console.log(`   System: ${system || 'all'}`);
console.log(`   Tenant: ${tenant}`);
console.log(`   Endpoint: POST ${path}\n`);

const options = {
  hostname: 'localhost',
  port: 5000,
  path: path,
  method: 'POST',
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
        console.log('✅ Replay successful!\n');
        console.log(`📊 Statistics:`);
        console.log(`   Files processed: ${response.stats.files_processed}`);
        console.log(`   Total records: ${response.stats.total_records}`);
        console.log(`   Unknown fields: ${response.stats.unknown_fields_count}\n`);
        
        if (response.stats.records_by_entity) {
          console.log('📈 Records by Entity:');
          Object.entries(response.stats.records_by_entity).forEach(([entity, count]) => {
            console.log(`   ${entity}: ${count}`);
          });
          console.log('');
        }
        
        if (response.stats.records_by_system) {
          console.log('🔌 Records by System:');
          Object.entries(response.stats.records_by_system).forEach(([system, count]) => {
            console.log(`   ${system}: ${count}`);
          });
          console.log('');
        }
        
        if (response.stats.files) {
          console.log('📁 Files:');
          response.stats.files.forEach(file => {
            console.log(`   ${file.filename} (${file.entity}/${file.system}): ${file.records} records`);
          });
        }
      } else {
        console.error(`❌ Replay failed (${res.statusCode})`);
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
