import os

output_dir = 'dist'
os.makedirs(output_dir, exist_ok=True)

with open(os.path.join(output_dir, 'index.html'), 'w') as f:
    f.write("<h1>Hello from Flask-generated static HTML</h1>")
