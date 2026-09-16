export type JobStatus =
  | "queued"
  | "preprocessing"
  | "running_brain"
  | "training_readout"
  | "running_baselines"
  | "running_control"
  | "finalizing"
  | "complete"
  | "failed";

export interface BrainInfo {
  dataset: string;
  published_neurons: number;
  runtime_neurons: number;
  runtime_edges: number;
  input_neurons: number;
  readout_neurons: number;
  weight_transform: string;
  sign_mode: string;
  reservoir_model: string;
  manifest_hash: string;
  leak: number;
  recurrent_gain: number;
  input_gain: number;
}

export interface DemoItem {
  id: string;
  name: string;
  description: string;
  time_column: string;
  target_column: string;
  sample_csv: string;
}

export interface ExperimentStatus {
  id: string;
  status: JobStatus;
  progress: number;
  message: string;
  created_at: string;
  updated_at: string;
  error?: string | null;
}

export interface ModelMetrics {
  mae: number;
  rmse: number;
  r2: number;
  smape: number;
  best_lag?: number;
  best_alpha?: number;
}

export interface EditorialVerdict {
  winner: "fly" | "persistence" | "autoregressive" | "control";
  verdict: string;
  headline: string;
  summary: string;
  control_summary?: string | null;
}

export interface ExperimentResultPayload {
  experiment_id: string;
  dataset: {
    rows_original: number;
    rows_simulated: number;
    target: string;
    time_column: string;
    features: string[];
    resampling_note?: string | null;
  };
  forecast: {
    horizon: number;
    values: number[];
    interval_lower: number[];
    interval_upper: number[];
    residual_std: number;
  };
  fly: ModelMetrics;
  baselines: {
    persistence: ModelMetrics;
    autoregressive_ridge: ModelMetrics;
  };
  control?: {
    type: string;
    metrics: ModelMetrics;
    future_forecast: number[];
  } | null;
  winner: string;
  editorial: EditorialVerdict;
  reservoir: {
    neurons: number;
    edges: number;
    input_neurons: number;
    readout_neurons: number;
    leak: number;
    recurrent_gain: number;
    input_gain: number;
    ridge_alpha: number;
    washout: number;
  };
  reproducibility: {
    seed: number;
    brain_manifest_hash: string;
    dataset_sha256: string;
    connectome_version: string;
    train_size: number;
    val_size: number;
    test_size: number;
  };
  timings: Record<string, number>;
}

export interface ChartPoint {
  time: string;
  step: number;
  actual?: number | null;
  flycast?: number | null;
  persistence?: number | null;
  autoregressive?: number | null;
  lower_95?: number | null;
  upper_95?: number | null;
  segment: "history" | "test" | "future";
}

export interface ActivityVizData {
  timesteps: number;
  mean_abs_activity: number[];
  max_abs_activity: number[];
  sample_activity: number[][];
  num_sampled_neurons: number;
}

export interface FullExperimentResponse {
  status: "complete";
  result: ExperimentResultPayload;
  chart: {
    history: ChartPoint[];
    test: ChartPoint[];
    future: ChartPoint[];
    activity_viz: ActivityVizData;
  };
}
