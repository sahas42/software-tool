import os
import subprocess
import signal

def kill_port(port):
    print(f"Searching for process on port {port}...")
    try:
        # Find the PID using netstat
        output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
        lines = output.strip().split('\n')
        pids = set()
        for line in lines:
            parts = line.split()
            if len(parts) > 4:
                pids.add(parts[-1])
        
        for pid in pids:
            print(f"  Found PID {pid}. Killing it...")
            subprocess.run(f"taskkill /F /PID {pid}", shell=True)
            print(f"  PID {pid} terminated.")
            
    except subprocess.CalledProcessError:
        print(f"  No process found on port {port}.")
    except Exception as e:
        print(f"  Error killing port {port}: {e}")

if __name__ == "__main__":
    kill_port(3000) # Next.js
    kill_port(5001) # Flask
    
    # Also delete the script itself
    try:
        os.remove(__file__)
    except:
        pass
    
    print("\nPorts cleared! You can now start your servers fresh.")
