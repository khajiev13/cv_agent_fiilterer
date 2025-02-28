# Resume Agent

## Neo4j Setup Instructions

The application requires a connection to a Neo4j database. Follow these steps to set up your connection:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up Neo4j:
   - If using Neo4j Desktop: Create and start a local database
   - If using Neo4j Aura: Create a database in [Neo4j Aura Console](https://console.neo4j.io)

3. Configure environment variables:
   - Copy the example environment file: `cp .env.example .env`
   - Edit `.env` file and update Neo4j connection details:
     ```
     NEO4J_URI=bolt://your-neo4j-instance:7687
     NEO4J_USER=neo4j
     NEO4J_PASSWORD=your-password
     ```

4. Run the application:
   ```bash
   streamlit run app/main.py
   ```

## Troubleshooting

If you see connection errors:
- Verify that your Neo4j instance is running
- Check that the URI, username, and password are correct in your `.env` file
- Ensure that your firewall allows connections to the Neo4j port (default: 7687)
