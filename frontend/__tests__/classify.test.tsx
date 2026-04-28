import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Classify from "@/pages/classify";
import { api } from "@/utils/api";
import { storage } from "@/utils/storage";

// Mock next/router
const mockPush = jest.fn();
jest.mock("next/router", () => ({
  useRouter: () => ({
    push: mockPush,
    pathname: "/classify",
    query: {},
  }),
}));

// Mock next-i18next
jest.mock("next-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => defaultValue || key,
  }),
  serverSideTranslations: async () => ({}),
}));

// Mock API
jest.mock("@/utils/api");
jest.mock("@/utils/storage");
jest.mock("@/lib/pwa-utils", () => ({
  pwaManager: {
    cacheClassification: jest.fn(),
  },
}));

// Mock components
jest.mock("@/components/ImageUpload", () => ({
  ImageUpload: ({ onImageSelect }: any) => (
    <div data-testid="image-upload">
      <button
        onClick={() => {
          const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
          onImageSelect(mockFile, "blob:test");
        }}
      >
        Upload Image
      </button>
    </div>
  ),
}));

jest.mock("@/components/ClassificationResult", () => ({
  ClassificationResult: ({ result }: any) => (
    <div data-testid="classification-result">
      {result.food || result.prediction}
    </div>
  ),
}));

jest.mock("@/components/ErrorMessage", () => ({
  ErrorMessage: ({ error, onRetry }: any) => (
    <div data-testid="error-message">
      {error.message}
      {onRetry && <button onClick={onRetry}>Retry</button>}
    </div>
  ),
}));

jest.mock("@/components/LanguageSwitcher", () => ({
  __esModule: true,
  default: () => <div data-testid="language-switcher">Language</div>,
}));

describe("Classify Page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (storage.get as jest.Mock).mockReturnValue([]);
    (storage.set as jest.Mock).mockReturnValue(true);
  });

  it("renders the classify page", () => {
    render(<Classify />);
    expect(screen.getByText("Classify Food")).toBeInTheDocument();
  });

  it("shows image upload component when no image is selected", () => {
    render(<Classify />);
    expect(screen.getByTestId("image-upload")).toBeInTheDocument();
  });

  it("allows image upload", () => {
    render(<Classify />);
    const uploadButton = screen.getByText("Upload Image");
    fireEvent.click(uploadButton);
    
    // After upload, the classify button should appear
    waitFor(() => {
      expect(screen.getByText("Classify Food")).toBeInTheDocument();
    });
  });

  it("handles classification success", async () => {
    const mockResponse = {
      data: {
        prediction: "Pizza",
        food: "Pizza",
        confidence: 0.95,
        calories: 285,
        timestamp: new Date().toISOString(),
        processing_time: 100,
        request_id: "test-123",
      },
      status: 200,
    };

    (api.post as jest.Mock).mockResolvedValue(mockResponse);

    render(<Classify />);
    
    // Upload image
    const uploadButton = screen.getByText("Upload Image");
    fireEvent.click(uploadButton);

    // Wait for classify button and click it
    await waitFor(() => {
      const classifyButtons = screen.getAllByText("Classify Food");
      fireEvent.click(classifyButtons[classifyButtons.length - 1]);
    });

    // Check if result is displayed
    await waitFor(() => {
      expect(screen.getByTestId("classification-result")).toBeInTheDocument();
      expect(screen.getByText("Pizza")).toBeInTheDocument();
    });
  });

  it("handles classification error", async () => {
    const mockError = {
      error: "Classification failed",
      status: 500,
    };

    (api.post as jest.Mock).mockResolvedValue(mockError);

    render(<Classify />);
    
    // Upload image
    const uploadButton = screen.getByText("Upload Image");
    fireEvent.click(uploadButton);

    // Click classify
    await waitFor(() => {
      const classifyButtons = screen.getAllByText("Classify Food");
      fireEvent.click(classifyButtons[classifyButtons.length - 1]);
    });

    // Check if error is displayed
    await waitFor(() => {
      expect(screen.getByTestId("error-message")).toBeInTheDocument();
    });
  });

  it("navigates back to home", () => {
    render(<Classify />);
    const backButton = screen.getByLabelText("Back to home");
    fireEvent.click(backButton);
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("loads history from storage on mount", () => {
    const mockHistory = [
      {
        id: 1,
        prediction: "Pizza",
        food: "Pizza",
        confidence: 0.95,
        timestamp: new Date().toISOString(),
        processing_time: 100,
        request_id: "test-1",
      },
    ];

    (storage.get as jest.Mock).mockReturnValue(mockHistory);

    render(<Classify />);
    
    expect(storage.get).toHaveBeenCalledWith("classification_history", []);
  });
});
