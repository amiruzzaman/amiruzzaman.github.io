# Currency Collection Application

## Getting Started

### Running the Application

1. **Main Application**:
   - Run `python server.py`
   - Access at `http://localhost:5000`
   - Login with credentials: `admin/admin` (at `http://localhost:5000/login`)
   - Successful login redirects to `http://localhost:5000/upload`

2. **Alternative Methods**:
   - Run `python main.py` then access `http://localhost:5000`
   - Run `index.html` directly after starting localhost

## Key Features

### Upload Functionality
- **File Upload**: `upload.py`
  - Upload images to country-specific folders
  - Access at `http://localhost:5000`

### Editing Features
- **Edit/Delete Entries**: `server.py`
  - Access at `http://localhost:5000/edit_json`
  - View, edit, and delete collection information
  - Drag a row to re-order

- **Image Editing**: `editnplace.py`
  - Crop and save images
  - Access via `http://localhost:5000/edit`

### Additional Tools
- **Drag & Drop**: `dragndrop.py`
  - Add images via drag and drop interface
  - Updates `coins.json` automatically

## Application Structure

### Main Components
- `server.py` - Primary application file (contains most functionality)
- `coins.json` - Database file storing all collection data
- `images/` - Directory where uploaded images are stored

### Supporting Files
- `main.py` - Alternative entry point
- `dragndrop.py` - Drag and drop functionality
- `editnplace.py` - Image cropping tool
- `upload.py` - Dedicated upload handler

## Notes
- Check `main.py` for additional implementation details
- All image uploads are organized into country-specific subfolders within `images/`