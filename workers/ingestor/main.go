package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"path/filepath"
	"strings"
	"time"
)

const safeIngestDir = "./data"

type IngestRequest struct {
	FilePath string `json:"file_path"`
}

type IngestResponse struct {
	Status  string `json:"status"`
	Bytes   int    `json:"bytes_processed"`
	Elapsed string `json:"elapsed"`
}

func ingestHandler(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	var req IngestRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid Request Payload", http.StatusBadRequest)
		return
	}

	// 🛡️ SECURITY: Prevent Path Traversal
	// 1. Get absolute path of the safe directory
	safeBase, err := filepath.Abs(safeIngestDir)
	if err != nil {
		http.Error(w, "Internal Configuration Error", http.StatusInternalServerError)
		return
	}

	// 2. Join base with user input and resolve to absolute
	targetPath, err := filepath.Abs(filepath.Join(safeBase, filepath.Base(req.FilePath)))
	if err != nil {
		http.Error(w, "Invalid File Path", http.StatusBadRequest)
		return
	}

	// 3. Verify the final path is still inside the safe directory
	if !strings.HasPrefix(targetPath, safeBase) {
		http.Error(w, "Security Breach: Unauthorized File Access Attempt", http.StatusForbidden)
		return
	}

	// High-speed file reading (Go Specialty)
	content, err := ioutil.ReadFile(targetPath)
	if err != nil {
		http.Error(w, "File Access Failed", http.StatusNotFound)
		return
	}

	elapsed := time.Since(start)
	log.Printf("GO_ENGINE | Processed %d bytes in %s", len(content), elapsed)

	json.NewEncoder(w).Encode(IngestResponse{
		Status:  "success",
		Bytes:   len(content),
		Elapsed: elapsed.String(),
	})
}

func main() {
	http.HandleFunc("/process", ingestHandler)
	port := "8081"
	fmt.Printf("🚀 Nexus Go Ingestor (Hardened) on port %s\n", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
